"""
MCP (Model Context Protocol) client implementation.

Provides functionality to:
- Connect to MCP servers via multiple transports
- Discover and call tools
- Manage resources
- Handle JSON-RPC 2.0 messaging
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    mime_type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str = ""
    params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.id is not None:
            result["id"] = self.id
        if self.params is not None:
            result["params"] = self.params
        return result


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: Any = None
    error: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JSONRPCResponse:
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )


class Transport:
    """Base class for MCP transports."""

    def send(self, message: dict[str, Any]) -> None:
        """Send a message."""
        raise NotImplementedError

    def receive(self) -> dict[str, Any]:
        """Receive a message."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the transport."""
        pass


class StdioTransport(Transport):
    """Stdio transport for MCP servers."""

    def __init__(self, command: str, args: list[str] | None = None):
        """
        Initialize stdio transport.

        Args:
            command: Command to run
            args: Command arguments
        """
        self.command = command
        self.args = args or []
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        """Start the server process."""
        cmd = [self.command] + self.args
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

    def send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server process not started")

        line = json.dumps(message) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()

    def receive(self) -> dict[str, Any]:
        """Receive a JSON-RPC message."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Server process not started")

        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Server closed connection")

        return json.loads(line)

    def close(self) -> None:
        """Close the server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


class MCPClient:
    """MCP client for connecting to servers."""

    def __init__(self, transport: Transport, server_name: str = "default"):
        """
        Initialize MCP client.

        Args:
            transport: Transport to use
            server_name: Server name for identification
        """
        self.transport = transport
        self.server_name = server_name
        self.request_id = 0
        self._tools: list[MCPTool] | None = None
        self._resources: list[MCPResource] | None = None

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def _send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> JSONRPCResponse:
        """
        Send JSON-RPC request.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            JSON-RPC response
        """
        request = JSONRPCRequest(
            id=self._next_id(), method=method, params=params
        )

        self.transport.send(request.to_dict())
        response_data = self.transport.receive()
        response = JSONRPCResponse.from_dict(response_data)

        if response.error:
            raise RuntimeError(f"RPC error: {response.error}")

        return response

    def initialize(self) -> dict[str, Any]:
        """
        Initialize connection to server.

        Returns:
            Server capabilities
        """
        response = self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "clawd-codex", "version": "0.1.0"},
                "capabilities": {},
            },
        )

        return response.result or {}

    def list_tools(self, force_refresh: bool = False) -> list[MCPTool]:
        """
        List available tools.

        Args:
            force_refresh: Force refresh from server

        Returns:
            List of MCP tools
        """
        if self._tools is not None and not force_refresh:
            return self._tools

        response = self._send_request("tools/list")
        tools_data = response.result.get("tools", [])

        self._tools = [
            MCPTool(
                name=tool["name"],
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
            )
            for tool in tools_data
        ]

        return self._tools

    def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Call a tool on the server.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        response = self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        return response.result or {}

    def list_resources(self, force_refresh: bool = False) -> list[MCPResource]:
        """
        List available resources.

        Args:
            force_refresh: Force refresh from server

        Returns:
            List of MCP resources
        """
        if self._resources is not None and not force_refresh:
            return self._resources

        response = self._send_request("resources/list")
        resources_data = response.result.get("resources", [])

        self._resources = [
            MCPResource(
                uri=res["uri"],
                name=res.get("name", ""),
                mime_type=res.get("mimeType"),
                description=res.get("description"),
            )
            for res in resources_data
        ]

        return self._resources

    def read_resource(self, uri: str) -> dict[str, Any]:
        """
        Read a resource from the server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        response = self._send_request("resources/read", {"uri": uri})
        return response.result or {}

    def close(self) -> None:
        """Close the client connection."""
        self.transport.close()
        self._tools = None
        self._resources = None


def create_stdio_client(
    command: str, args: list[str] | None = None, server_name: str = "default"
) -> MCPClient:
    """
    Create an MCP client with stdio transport.

    Args:
        command: Command to run
        args: Command arguments
        server_name: Server name

    Returns:
        MCPClient instance
    """
    transport = StdioTransport(command, args)
    transport.start()

    client = MCPClient(transport, server_name)
    client.initialize()

    return client
