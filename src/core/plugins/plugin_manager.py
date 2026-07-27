"""Plugin discovery, loading, and shutdown orchestration."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Optional, cast

from src.core.plugins.exceptions import PluginError, PluginIncompatibleError
from src.core.plugins.plugin_base import JunEduPlugin, PluginFactory
from src.core.plugins.plugin_context import PluginContext
from src.core.plugins.plugin_manifest import PluginManifest
from src.core.plugins.ui_registry import UIRegistry
from src.core.plugins.worker_manager import WorkerManager

PLUGIN_API_VERSION = "1"


class PluginManager:
    """Discover, load, and isolate optional Jun Edu plugins."""

    def __init__(
        self,
        plugins_dir: Path,
        ui_registry: UIRegistry,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._plugins_dir = plugins_dir
        self._ui_registry = ui_registry
        self._logger = logger or logging.getLogger("junedu.plugins")
        self._workers = WorkerManager()
        self._plugins: Dict[str, JunEduPlugin] = {}

    def discover_and_load(self) -> None:
        """Load enabled plugins from the plugin directory."""
        if not self._plugins_dir.is_dir():
            self._logger.info("Plugin directory does not exist: %s", self._plugins_dir)
            return

        for plugin_dir in sorted(self._plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            try:
                self._load_plugin(plugin_dir)
            except PluginError as exc:
                self._logger.exception("Plugin skipped from %s: %s", plugin_dir, exc)
            except Exception as exc:
                self._logger.exception("Unexpected plugin load failure in %s: %s", plugin_dir, exc)

    def shutdown(self) -> None:
        """Shutdown loaded plugins and workers."""
        for plugin_id, plugin in list(self._plugins.items()):
            try:
                plugin.shutdown()
            except Exception as exc:
                self._logger.exception("Plugin shutdown failed for %s: %s", plugin_id, exc)
            self._ui_registry.unregister_plugin(plugin_id)
            self._workers.shutdown_plugin(plugin_id)
        self._plugins.clear()
        self._workers.shutdown_all()

    def _load_plugin(self, plugin_dir: Path) -> None:
        manifest = PluginManifest.load(plugin_dir / "plugin.json")
        if not manifest.enabled:
            self._logger.info("Plugin disabled: %s", manifest.plugin_id)
            return
        if manifest.api_version != PLUGIN_API_VERSION:
            raise PluginIncompatibleError(
                f"Plugin {manifest.plugin_id} targets API {manifest.api_version}; "
                f"supported API is {PLUGIN_API_VERSION}"
            )
        if manifest.execution != "in_process":
            self._logger.info(
                "Plugin %s uses process execution and has no in-process UI entry",
                manifest.plugin_id,
            )
            return
        if manifest.plugin_id in self._plugins:
            raise PluginError(f"Duplicate plugin id: {manifest.plugin_id}")

        module = self._load_module(manifest, plugin_dir)
        factory_object = getattr(module, "create_plugin", None)
        if factory_object is None or not callable(factory_object):
            raise PluginError("Plugin module must export callable create_plugin")

        factory = cast(PluginFactory, factory_object)
        plugin = _create_plugin(factory)
        if plugin.plugin_id != manifest.plugin_id:
            raise PluginError(
                f"Plugin id mismatch: manifest has {manifest.plugin_id}, "
                f"plugin has {plugin.plugin_id}"
            )

        context = PluginContext(
            plugin_id=manifest.plugin_id,
            plugin_dir=plugin_dir,
            ui=self._ui_registry,
            logger=self._logger.getChild(manifest.plugin_id),
            workers=self._workers,
        )
        plugin.initialize(context)
        self._plugins[manifest.plugin_id] = plugin
        self._logger.info("Loaded plugin: %s", manifest.plugin_id)

    def _load_module(self, manifest: PluginManifest, plugin_dir: Path) -> ModuleType:
        entry_path = (plugin_dir / manifest.entry).resolve()
        module_name = f"junedu_plugin_{manifest.plugin_id.replace('-', '_').replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise PluginError(f"Cannot import plugin module: {entry_path}")

        module = importlib.util.module_from_spec(spec)
        previous_path = list(sys.path)
        sys.modules[module_name] = module
        try:
            sys.path.insert(0, str(plugin_dir))
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        finally:
            sys.path = previous_path
        return module


def _create_plugin(factory: PluginFactory) -> JunEduPlugin:
    plugin = factory()
    if not isinstance(plugin, JunEduPlugin):
        raise PluginError("create_plugin must return a JunEduPlugin instance")
    return plugin
