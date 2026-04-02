"""Tests for mcp_client module."""

import unittest
from unittest.mock import Mock, MagicMock, patch

from src.mcp_client import (
    MCPTool,
    MCPResource,
    JSONRPCRequest,
    JSONRPCResponse,
    Transport,
    MCPClient,
)


class TestMCPClient(unittest.TestCase):
    """Test cases for MCP client."""

    def test_create_mcp_tool(self):
        """Test creating an MCP tool."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )

        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "A test tool")

    def test_create_mcp_resource(self):
        """Test creating an MCP resource."""
        resource = MCPResource(
            uri="file:///test.txt",
            name="test.txt",
            mime_type="text/plain",
        )

        self.assertEqual(resource.uri, "file:///test.txt")
        self.assertEqual(resource.name, "test.txt")

    def test_jsonrpc_request_to_dict(self):
        """Test JSON-RPC request serialization."""
        request = JSONRPCRequest(
            id=1, method="test", params={"key": "value"}
        )

        data = request.to_dict()

        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["method"], "test")
        self.assertEqual(data["params"], {"key": "value"})

    def test_jsonrpc_response_from_dict(self):
        """Test JSON-RPC response deserialization."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"},
        }

        response = JSONRPCResponse.from_dict(data)

        self.assertEqual(response.jsonrpc, "2.0")
        self.assertEqual(response.id, 1)
        self.assertEqual(response.result, {"status": "ok"})

    def test_jsonrpc_response_with_error(self):
        """Test JSON-RPC error response."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid Request"},
        }

        response = JSONRPCResponse.from_dict(data)

        self.assertIsNotNone(response.error)
        self.assertEqual(response.error["code"], -32600)

    def test_mcp_client_create(self):
        """Test creating MCP client."""
        transport = Mock(spec=Transport)
        client = MCPClient(transport, "test-server")

        self.assertEqual(client.server_name, "test-server")
        self.assertEqual(client.request_id, 0)

    def test_mcp_client_next_id(self):
        """Test request ID generation."""
        transport = Mock(spec=Transport)
        client = MCPClient(transport)

        id1 = client._next_id()
        id2 = client._next_id()

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)

    def test_mcp_client_send_request(self):
        """Test sending JSON-RPC request."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}
        )

        client = MCPClient(transport)
        response = client._send_request("test_method", {"key": "value"})

        # Check request was sent
        transport.send.assert_called_once()
        sent_data = transport.send.call_args[0][0]
        self.assertEqual(sent_data["method"], "test_method")
        self.assertEqual(sent_data["params"], {"key": "value"})

        # Check response
        self.assertEqual(response.result, {"status": "ok"})

    def test_mcp_client_send_request_error(self):
        """Test handling JSON-RPC error."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32600, "message": "Invalid Request"},
            }
        )

        client = MCPClient(transport)

        with self.assertRaises(RuntimeError) as context:
            client._send_request("test_method")

        self.assertIn("RPC error", str(context.exception))

    def test_mcp_client_initialize(self):
        """Test client initialization."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": "2024-11-05"},
            }
        )

        client = MCPClient(transport)
        result = client.initialize()

        # Check initialization request
        transport.send.assert_called_once()
        sent_data = transport.send.call_args[0][0]
        self.assertEqual(sent_data["method"], "initialize")
        self.assertIn("protocolVersion", sent_data["params"])

        # Check result
        self.assertEqual(result["protocolVersion"], "2024-11-05")

    def test_mcp_client_list_tools(self):
        """Test listing tools."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {
                            "name": "tool1",
                            "description": "Tool 1",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                },
            }
        )

        client = MCPClient(transport)
        tools = client.list_tools()

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "tool1")

    def test_mcp_client_call_tool(self):
        """Test calling a tool."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"output": "result"},
            }
        )

        client = MCPClient(transport)
        result = client.call_tool("test_tool", {"arg": "value"})

        # Check request
        transport.send.assert_called_once()
        sent_data = transport.send.call_args[0][0]
        self.assertEqual(sent_data["method"], "tools/call")
        self.assertEqual(sent_data["params"]["name"], "test_tool")

        # Check result
        self.assertEqual(result, {"output": "result"})

    def test_mcp_client_list_resources(self):
        """Test listing resources."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "resources": [
                        {
                            "uri": "file:///test.txt",
                            "name": "test.txt",
                        }
                    ]
                },
            }
        )

        client = MCPClient(transport)
        resources = client.list_resources()

        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].uri, "file:///test.txt")

    def test_mcp_client_read_resource(self):
        """Test reading a resource."""
        transport = Mock(spec=Transport)
        transport.send = Mock()
        transport.receive = Mock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"contents": ["test content"]},
            }
        )

        client = MCPClient(transport)
        result = client.read_resource("file:///test.txt")

        # Check request
        transport.send.assert_called_once()
        sent_data = transport.send.call_args[0][0]
        self.assertEqual(sent_data["method"], "resources/read")

        # Check result
        self.assertEqual(result, {"contents": ["test content"]})


if __name__ == "__main__":
    unittest.main()
