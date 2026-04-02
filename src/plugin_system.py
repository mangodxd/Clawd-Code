"""
Python plugin system for extending Clawd Codex.

Provides functionality to:
- Discover plugins from directories
- Load plugin modules safely
- Register custom tools, commands, and hooks
- Manage plugin lifecycle
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class PluginMetadata:
    """Plugin metadata."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_dir: Path | None = None


@dataclass
class Plugin:
    """Loaded plugin."""

    metadata: PluginMetadata
    module: Any
    tools: list[dict[str, Any]] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    hooks: list[dict[str, Any]] = field(default_factory=list)


class PluginLoader:
    """Discovers and loads plugins."""

    def __init__(self, plugin_dirs: list[Path] | None = None):
        """
        Initialize plugin loader.

        Args:
            plugin_dirs: Directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or []
        self.loaded_plugins: dict[str, Plugin] = {}

    def add_plugin_dir(self, directory: Path) -> None:
        """Add a plugin directory."""
        if directory not in self.plugin_dirs:
            self.plugin_dirs.append(directory)

    def discover_plugins(self) -> list[Path]:
        """
        Discover plugin directories.

        Returns:
            List of plugin directory paths
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            # Look for plugin directories (contain __init__.py or plugin.py)
            for item in plugin_dir.iterdir():
                if item.is_dir():
                    init_file = item / "__init__.py"
                    plugin_file = item / "plugin.py"

                    if init_file.exists() or plugin_file.exists():
                        discovered.append(item)

        return discovered

    def load_plugin_metadata(self, plugin_dir: Path) -> PluginMetadata | None:
        """
        Load plugin metadata from directory.

        Args:
            plugin_dir: Plugin directory

        Returns:
            PluginMetadata or None if invalid
        """
        # Look for metadata files
        metadata_file = plugin_dir / "plugin.json"

        if metadata_file.exists():
            try:
                import json

                with open(metadata_file) as f:
                    data = json.load(f)

                return PluginMetadata(
                    name=data.get("name", plugin_dir.name),
                    version=data.get("version", "0.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    plugin_dir=plugin_dir,
                )
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback to directory name
        return PluginMetadata(
            name=plugin_dir.name,
            version="0.0.0",
            plugin_dir=plugin_dir,
        )

    def load_plugin_module(self, plugin_dir: Path) -> Any | None:
        """
        Load plugin module.

        Args:
            plugin_dir: Plugin directory

        Returns:
            Plugin module or None if loading fails
        """
        plugin_name = plugin_dir.name

        # Try plugin.py first
        plugin_file = plugin_dir / "plugin.py"
        if plugin_file.exists():
            module_name = f"clawd_plugin_{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module

        # Try package
        init_file = plugin_dir / "__init__.py"
        if init_file.exists():
            module_name = f"clawd_plugin_{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, init_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module

        return None

    def load_plugin(self, plugin_dir: Path) -> Plugin | None:
        """
        Load a plugin from directory.

        Args:
            plugin_dir: Plugin directory

        Returns:
            Plugin or None if loading fails
        """
        # Load metadata
        metadata = self.load_plugin_metadata(plugin_dir)
        if not metadata:
            return None

        # Load module
        module = self.load_plugin_module(plugin_dir)
        if not module:
            return None

        # Extract plugin components
        tools = []
        commands = []
        hooks = []

        # Look for plugin registration
        if hasattr(module, "register_plugin"):
            # Call registration function
            registration = module.register_plugin()
            tools = registration.get("tools", [])
            commands = registration.get("commands", [])
            hooks = registration.get("hooks", [])

        # Also check for direct attributes
        if hasattr(module, "TOOLS"):
            tools.extend(module.TOOLS)
        if hasattr(module, "COMMANDS"):
            commands.extend(module.COMMANDS)
        if hasattr(module, "HOOKS"):
            hooks.extend(module.HOOKS)

        plugin = Plugin(
            metadata=metadata,
            module=module,
            tools=tools,
            commands=commands,
            hooks=hooks,
        )

        self.loaded_plugins[metadata.name] = plugin
        return plugin

    def load_all_plugins(self) -> list[Plugin]:
        """
        Load all discovered plugins.

        Returns:
            List of loaded plugins
        """
        discovered = self.discover_plugins()
        loaded = []

        for plugin_dir in discovered:
            plugin = self.load_plugin(plugin_dir)
            if plugin:
                loaded.append(plugin)

        return loaded

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self.loaded_plugins.get(name)

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was unloaded
        """
        if name in self.loaded_plugins:
            del self.loaded_plugins[name]
            return True
        return False


class PluginManager:
    """Manages plugin lifecycle and registration."""

    def __init__(self, loader: PluginLoader | None = None):
        """
        Initialize plugin manager.

        Args:
            loader: Plugin loader instance
        """
        self.loader = loader or PluginLoader()
        self.tool_registry: dict[str, Any] = {}
        self.command_registry: dict[str, Any] = {}
        self.hook_registry: dict[str, Any] = {}

    def register_plugin_tools(self, plugin: Plugin) -> None:
        """Register plugin tools."""
        for tool in plugin.tools:
            tool_name = tool.get("name")
            if tool_name:
                self.tool_registry[f"{plugin.metadata.name}.{tool_name}"] = tool

    def register_plugin_commands(self, plugin: Plugin) -> None:
        """Register plugin commands."""
        for command in plugin.commands:
            command_name = command.get("name")
            if command_name:
                self.command_registry[f"{plugin.metadata.name}.{command_name}"] = command

    def register_plugin_hooks(self, plugin: Plugin) -> None:
        """Register plugin hooks."""
        for hook in plugin.hooks:
            hook_name = hook.get("name")
            if hook_name:
                self.hook_registry[f"{plugin.metadata.name}.{hook_name}"] = hook

    def load_and_register_plugins(self) -> list[Plugin]:
        """
        Load and register all plugins.

        Returns:
            List of loaded plugins
        """
        plugins = self.loader.load_all_plugins()

        for plugin in plugins:
            self.register_plugin_tools(plugin)
            self.register_plugin_commands(plugin)
            self.register_plugin_hooks(plugin)

        return plugins

    def get_tool(self, name: str) -> Any | None:
        """Get a registered tool."""
        return self.tool_registry.get(name)

    def get_command(self, name: str) -> Any | None:
        """Get a registered command."""
        return self.command_registry.get(name)

    def get_hook(self, name: str) -> Any | None:
        """Get a registered hook."""
        return self.hook_registry.get(name)


def create_plugin_manager(plugin_dirs: list[Path] | None = None) -> PluginManager:
    """
    Create a plugin manager.

    Args:
        plugin_dirs: Optional plugin directories

    Returns:
        PluginManager instance
    """
    loader = PluginLoader(plugin_dirs)
    return PluginManager(loader)
