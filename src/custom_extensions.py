"""
Custom extension system for user-defined tools, commands, and hooks.

Provides functionality to:
- Define custom tools from Python functions
- Define custom commands with handlers
- Define custom hooks for tool execution
- Manage extension lifecycle
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CustomTool:
    """User-defined tool."""

    name: str
    description: str
    function: Callable
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class CustomCommand:
    """User-defined command."""

    name: str
    description: str
    handler: Callable
    usage: str = ""
    examples: list[str] | None = None


@dataclass(frozen=True)
class CustomHook:
    """User-defined hook."""

    name: str
    event: str  # "pre_tool_use", "post_tool_use", etc.
    handler: Callable
    priority: int = 50  # Higher = earlier execution


class ExtensionRegistry:
    """Registry for custom extensions."""

    def __init__(self):
        """Initialize extension registry."""
        self.tools: dict[str, CustomTool] = {}
        self.commands: dict[str, CustomCommand] = {}
        self.hooks: dict[str, list[CustomHook]] = {}

    def register_tool(self, tool: CustomTool) -> None:
        """Register a custom tool."""
        self.tools[tool.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a custom tool."""
        return self.tools.pop(name, None) is not None

    def register_command(self, command: CustomCommand) -> None:
        """Register a custom command."""
        self.commands[command.name] = command

    def unregister_command(self, name: str) -> bool:
        """Unregister a custom command."""
        return self.commands.pop(name, None) is not None

    def register_hook(self, hook: CustomHook) -> None:
        """Register a custom hook."""
        if hook.event not in self.hooks:
            self.hooks[hook.event] = []

        # Insert in priority order
        hooks = self.hooks[hook.event]
        for i, existing in enumerate(hooks):
            if hook.priority > existing.priority:
                hooks.insert(i, hook)
                return

        hooks.append(hook)

    def unregister_hook(self, name: str, event: str | None = None) -> int:
        """
        Unregister a custom hook.

        Args:
            name: Hook name
            event: Optional event to remove from (all events if None)

        Returns:
            Number of hooks removed
        """
        removed = 0

        if event:
            if event in self.hooks:
                before = len(self.hooks[event])
                self.hooks[event] = [h for h in self.hooks[event] if h.name != name]
                removed = before - len(self.hooks[event])
        else:
            for event_name in self.hooks:
                before = len(self.hooks[event_name])
                self.hooks[event_name] = [
                    h for h in self.hooks[event_name] if h.name != name
                ]
                removed += before - len(self.hooks[event_name])

        return removed

    def get_tool(self, name: str) -> CustomTool | None:
        """Get a registered tool."""
        return self.tools.get(name)

    def get_command(self, name: str) -> CustomCommand | None:
        """Get a registered command."""
        return self.commands.get(name)

    def get_hooks(self, event: str) -> list[CustomHook]:
        """Get hooks for an event."""
        return self.hooks.get(event, [])


def tool(
    name: str,
    description: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
):
    """
    Decorator to define a custom tool.

    Args:
        name: Tool name
        description: Tool description
        input_schema: Optional input schema
        output_schema: Optional output schema

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> CustomTool:
        return CustomTool(
            name=name,
            description=description,
            function=func,
            input_schema=input_schema,
            output_schema=output_schema,
        )

    return decorator


def command(
    name: str,
    description: str,
    usage: str = "",
    examples: list[str] | None = None,
):
    """
    Decorator to define a custom command.

    Args:
        name: Command name
        description: Command description
        usage: Command usage string
        examples: Optional usage examples

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> CustomCommand:
        return CustomCommand(
            name=name,
            description=description,
            handler=func,
            usage=usage,
            examples=examples,
        )

    return decorator


def hook(
    name: str,
    event: str,
    priority: int = 50,
):
    """
    Decorator to define a custom hook.

    Args:
        name: Hook name
        event: Event name (e.g., "pre_tool_use", "post_tool_use")
        priority: Hook priority (higher = earlier)

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> CustomHook:
        return CustomHook(
            name=name,
            event=event,
            handler=func,
            priority=priority,
        )

    return decorator


def create_extension_registry() -> ExtensionRegistry:
    """Create an extension registry."""
    return ExtensionRegistry()
