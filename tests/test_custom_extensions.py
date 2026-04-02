"""Tests for custom_extensions module."""

import unittest
from unittest.mock import Mock

from src.custom_extensions import (
    CustomTool,
    CustomCommand,
    CustomHook,
    ExtensionRegistry,
    tool,
    command,
    hook,
    create_extension_registry,
)


class TestCustomExtensions(unittest.TestCase):
    """Test cases for custom extensions."""

    def test_create_custom_tool(self):
        """Test creating a custom tool."""
        func = Mock()
        tool_instance = CustomTool(
            name="test_tool",
            description="Test tool",
            function=func,
        )

        self.assertEqual(tool_instance.name, "test_tool")
        self.assertEqual(tool_instance.description, "Test tool")
        self.assertEqual(tool_instance.function, func)

    def test_create_custom_command(self):
        """Test creating a custom command."""
        handler = Mock()
        command_instance = CustomCommand(
            name="test_command",
            description="Test command",
            handler=handler,
        )

        self.assertEqual(command_instance.name, "test_command")
        self.assertEqual(command_instance.handler, handler)

    def test_create_custom_hook(self):
        """Test creating a custom hook."""
        handler = Mock()
        hook_instance = CustomHook(
            name="test_hook",
            event="pre_tool_use",
            handler=handler,
        )

        self.assertEqual(hook_instance.name, "test_hook")
        self.assertEqual(hook_instance.event, "pre_tool_use")

    def test_create_extension_registry(self):
        """Test creating extension registry."""
        registry = create_extension_registry()

        self.assertIsInstance(registry, ExtensionRegistry)
        self.assertEqual(len(registry.tools), 0)

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ExtensionRegistry()
        tool_instance = CustomTool(
            name="test", description="Test", function=Mock()
        )

        registry.register_tool(tool_instance)

        self.assertIn("test", registry.tools)

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ExtensionRegistry()
        tool_instance = CustomTool(
            name="test", description="Test", function=Mock()
        )

        registry.register_tool(tool_instance)
        result = registry.unregister_tool("test")

        self.assertTrue(result)
        self.assertNotIn("test", registry.tools)

    def test_unregister_tool_missing(self):
        """Test unregistering missing tool."""
        registry = ExtensionRegistry()
        result = registry.unregister_tool("nonexistent")

        self.assertFalse(result)

    def test_register_command(self):
        """Test registering a command."""
        registry = ExtensionRegistry()
        command_instance = CustomCommand(
            name="test", description="Test", handler=Mock()
        )

        registry.register_command(command_instance)

        self.assertIn("test", registry.commands)

    def test_unregister_command(self):
        """Test unregistering a command."""
        registry = ExtensionRegistry()
        command_instance = CustomCommand(
            name="test", description="Test", handler=Mock()
        )

        registry.register_command(command_instance)
        result = registry.unregister_command("test")

        self.assertTrue(result)

    def test_register_hook(self):
        """Test registering a hook."""
        registry = ExtensionRegistry()
        hook_instance = CustomHook(
            name="test", event="pre_tool_use", handler=Mock()
        )

        registry.register_hook(hook_instance)

        self.assertIn("pre_tool_use", registry.hooks)
        self.assertEqual(len(registry.hooks["pre_tool_use"]), 1)

    def test_register_hook_priority(self):
        """Test hook priority ordering."""
        registry = ExtensionRegistry()

        hook1 = CustomHook(name="hook1", event="test", handler=Mock(), priority=10)
        hook2 = CustomHook(name="hook2", event="test", handler=Mock(), priority=50)
        hook3 = CustomHook(name="hook3", event="test", handler=Mock(), priority=30)

        # Register out of order
        registry.register_hook(hook1)
        registry.register_hook(hook2)
        registry.register_hook(hook3)

        # Should be ordered by priority (descending)
        hooks = registry.get_hooks("test")
        self.assertEqual(hooks[0].name, "hook2")  # priority 50
        self.assertEqual(hooks[1].name, "hook3")  # priority 30
        self.assertEqual(hooks[2].name, "hook1")  # priority 10

    def test_unregister_hook(self):
        """Test unregistering a hook."""
        registry = ExtensionRegistry()
        hook_instance = CustomHook(
            name="test", event="pre_tool_use", handler=Mock()
        )

        registry.register_hook(hook_instance)
        removed = registry.unregister_hook("test")

        self.assertEqual(removed, 1)
        self.assertEqual(len(registry.hooks["pre_tool_use"]), 0)

    def test_get_tool(self):
        """Test getting a registered tool."""
        registry = ExtensionRegistry()
        tool_instance = CustomTool(
            name="test", description="Test", function=Mock()
        )

        registry.register_tool(tool_instance)
        result = registry.get_tool("test")

        self.assertEqual(result, tool_instance)

    def test_get_command(self):
        """Test getting a registered command."""
        registry = ExtensionRegistry()
        command_instance = CustomCommand(
            name="test", description="Test", handler=Mock()
        )

        registry.register_command(command_instance)
        result = registry.get_command("test")

        self.assertEqual(result, command_instance)

    def test_get_hooks(self):
        """Test getting registered hooks."""
        registry = ExtensionRegistry()
        hook_instance = CustomHook(
            name="test", event="pre_tool_use", handler=Mock()
        )

        registry.register_hook(hook_instance)
        hooks = registry.get_hooks("pre_tool_use")

        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0], hook_instance)

    def test_tool_decorator(self):
        """Test tool decorator."""
        @tool("my_tool", "My test tool")
        def my_func():
            return "result"

        self.assertIsInstance(my_func, CustomTool)
        self.assertEqual(my_func.name, "my_tool")
        self.assertEqual(my_func.description, "My test tool")

    def test_command_decorator(self):
        """Test command decorator."""
        @command("my_command", "My test command")
        def my_handler():
            return "result"

        self.assertIsInstance(my_handler, CustomCommand)
        self.assertEqual(my_handler.name, "my_command")

    def test_hook_decorator(self):
        """Test hook decorator."""
        @hook("my_hook", "pre_tool_use", priority=100)
        def my_hook_func():
            pass

        self.assertIsInstance(my_hook_func, CustomHook)
        self.assertEqual(my_hook_func.name, "my_hook")
        self.assertEqual(my_hook_func.event, "pre_tool_use")
        self.assertEqual(my_hook_func.priority, 100)


if __name__ == "__main__":
    unittest.main()
