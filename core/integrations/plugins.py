"""Plugin loading system for NexusOS extensions."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class NexusPlugin:
    """Base class all NexusOS plugins must extend."""

    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""

    def on_load(self, nexus: Any) -> None:
        """Called when the plugin is loaded. Override to initialize."""

    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override to cleanup."""

    def get_commands(self) -> Dict[str, Callable]:
        """Return a dict of command_name -> handler the plugin provides."""
        return {}

    def get_workflows(self) -> List[Dict]:
        """Return workflow definitions provided by this plugin."""
        return []


class PluginManager:
    """Discovers, loads, and manages NexusOS plugins."""

    def __init__(self, plugin_dir: Optional[str] = None) -> None:
        settings = get_settings()
        self.plugin_dir = Path(plugin_dir or settings.plugin_dir)
        self._plugins: Dict[str, NexusPlugin] = {}
        self._commands: Dict[str, Callable] = {}
        self._nexus_ref: Any = None

    def set_nexus(self, nexus: Any) -> None:
        self._nexus_ref = nexus

    def discover_and_load(self) -> int:
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return 0

        loaded = 0
        for plugin_path in self.plugin_dir.glob("*.py"):
            if plugin_path.name.startswith("_"):
                continue
            try:
                self.load_plugin_file(plugin_path)
                loaded += 1
            except Exception as exc:
                logger.error("Failed to load plugin %s: %s", plugin_path.name, exc)

        logger.info("Loaded %d plugins from %s", loaded, self.plugin_dir)
        return loaded

    def load_plugin_file(self, path: Path) -> Optional[NexusPlugin]:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                inspect.isclass(attr)
                and issubclass(attr, NexusPlugin)
                and attr is not NexusPlugin
            ):
                instance = attr()
                self._register_plugin(instance)
                return instance

        return None

    def _register_plugin(self, plugin: NexusPlugin) -> None:
        plugin_name = plugin.name
        self._plugins[plugin_name] = plugin
        commands = plugin.get_commands()
        self._commands.update(commands)

        if self._nexus_ref:
            plugin.on_load(self._nexus_ref)

        logger.info(
            "Plugin '%s' v%s loaded (%d commands)",
            plugin_name,
            plugin.version,
            len(commands),
        )

    def unload_plugin(self, plugin_name: str) -> bool:
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return False

        for cmd in plugin.get_commands():
            self._commands.pop(cmd, None)

        plugin.on_unload()
        del self._plugins[plugin_name]
        logger.info("Plugin '%s' unloaded", plugin_name)
        return True

    def get_command(self, name: str) -> Optional[Callable]:
        return self._commands.get(name)

    def list_plugins(self) -> List[Dict]:
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "commands": list(p.get_commands().keys()),
            }
            for p in self._plugins.values()
        ]

    def list_commands(self) -> List[str]:
        return list(self._commands.keys())
