"""Tests for plugin_system module."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from src.plugin_system import (
    PluginMetadata,
    Plugin,
    PluginLoader,
    PluginManager,
    create_plugin_manager,
)


class TestPluginSystem(unittest.TestCase):
    """Test cases for plugin system."""

    def test_create_plugin_metadata(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
        )

        self.assertEqual(metadata.name, "test_plugin")
        self.assertEqual(metadata.version, "1.0.0")

    def test_create_plugin(self):
        """Test creating a plugin."""
        metadata = PluginMetadata(name="test", version="1.0")
        module = Mock()
        plugin = Plugin(metadata=metadata, module=module)

        self.assertEqual(plugin.metadata.name, "test")
        self.assertEqual(len(plugin.tools), 0)

    def test_create_plugin_loader(self):
        """Test creating a plugin loader."""
        loader = PluginLoader()

        self.assertEqual(len(loader.plugin_dirs), 0)
        self.assertEqual(len(loader.loaded_plugins), 0)

    def test_add_plugin_dir(self):
        """Test adding plugin directory."""
        loader = PluginLoader()
        test_dir = Path("/tmp/plugins")

        loader.add_plugin_dir(test_dir)

        self.assertIn(test_dir, loader.plugin_dirs)

    def test_discover_plugins_empty(self):
        """Test discovering plugins when none exist."""
        loader = PluginLoader([Path("/nonexistent")])
        discovered = loader.discover_plugins()

        self.assertEqual(len(discovered), 0)

    def test_load_plugin_metadata_missing(self):
        """Test loading metadata from missing plugin."""
        loader = PluginLoader()
        plugin_dir = Path("/nonexistent/plugin")

        metadata = loader.load_plugin_metadata(plugin_dir)

        # Should create fallback metadata
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.name, "plugin")

    def test_load_plugin_module_missing(self):
        """Test loading module from missing plugin."""
        loader = PluginLoader()
        plugin_dir = Path("/nonexistent/plugin")

        module = loader.load_plugin_module(plugin_dir)

        self.assertIsNone(module)

    def test_load_plugin_missing(self):
        """Test loading missing plugin."""
        loader = PluginLoader()
        plugin_dir = Path("/nonexistent/plugin")

        plugin = loader.load_plugin(plugin_dir)

        self.assertIsNone(plugin)

    def test_get_plugin_empty(self):
        """Test getting non-existent plugin."""
        loader = PluginLoader()
        plugin = loader.get_plugin("nonexistent")

        self.assertIsNone(plugin)

    def test_unload_plugin_missing(self):
        """Test unloading non-existent plugin."""
        loader = PluginLoader()
        result = loader.unload_plugin("nonexistent")

        self.assertFalse(result)

    def test_create_plugin_manager(self):
        """Test creating plugin manager."""
        manager = create_plugin_manager()

        self.assertIsInstance(manager, PluginManager)
        self.assertIsInstance(manager.loader, PluginLoader)

    def test_plugin_manager_empty_registries(self):
        """Test plugin manager has empty registries."""
        manager = PluginManager()

        self.assertEqual(len(manager.tool_registry), 0)
        self.assertEqual(len(manager.command_registry), 0)
        self.assertEqual(len(manager.hook_registry), 0)

    def test_register_plugin_tools(self):
        """Test registering plugin tools."""
        manager = PluginManager()
        metadata = PluginMetadata(name="test_plugin", version="1.0")
        module = Mock()

        plugin = Plugin(
            metadata=metadata,
            module=module,
            tools=[{"name": "test_tool", "function": Mock()}],
        )

        manager.register_plugin_tools(plugin)

        self.assertIn("test_plugin.test_tool", manager.tool_registry)

    def test_register_plugin_commands(self):
        """Test registering plugin commands."""
        manager = PluginManager()
        metadata = PluginMetadata(name="test_plugin", version="1.0")
        module = Mock()

        plugin = Plugin(
            metadata=metadata,
            module=module,
            commands=[{"name": "test_command", "handler": Mock()}],
        )

        manager.register_plugin_commands(plugin)

        self.assertIn("test_plugin.test_command", manager.command_registry)

    def test_register_plugin_hooks(self):
        """Test registering plugin hooks."""
        manager = PluginManager()
        metadata = PluginMetadata(name="test_plugin", version="1.0")
        module = Mock()

        plugin = Plugin(
            metadata=metadata,
            module=module,
            hooks=[{"name": "test_hook", "handler": Mock()}],
        )

        manager.register_plugin_hooks(plugin)

        self.assertIn("test_plugin.test_hook", manager.hook_registry)

    def test_get_tool(self):
        """Test getting registered tool."""
        manager = PluginManager()
        test_tool = {"name": "test"}

        manager.tool_registry["test_tool"] = test_tool
        result = manager.get_tool("test_tool")

        self.assertEqual(result, test_tool)

    def test_get_command(self):
        """Test getting registered command."""
        manager = PluginManager()
        test_command = {"name": "test"}

        manager.command_registry["test_command"] = test_command
        result = manager.get_command("test_command")

        self.assertEqual(result, test_command)

    def test_get_hook(self):
        """Test getting registered hook."""
        manager = PluginManager()
        test_hook = {"name": "test"}

        manager.hook_registry["test_hook"] = test_hook
        result = manager.get_hook("test_hook")

        self.assertEqual(result, test_hook)


if __name__ == "__main__":
    unittest.main()
