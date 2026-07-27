"""Context object passed to plugins during initialization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.core.plugins.ui_registry import UIRegistry
from src.core.plugins.worker_manager import WorkerManager


@dataclass(frozen=True)
class PluginContext:
    """Application services exposed to a single plugin."""

    plugin_id: str
    plugin_dir: Path
    ui: UIRegistry
    logger: logging.Logger
    workers: WorkerManager

    def get_resource_path(self, relative_path: str) -> str:
        """Return a resource path inside the plugin directory."""
        candidate = (self.plugin_dir / relative_path).resolve()
        plugin_root = self.plugin_dir.resolve()
        try:
            candidate.relative_to(plugin_root)
        except ValueError as exc:
            raise ValueError("Plugin resource path must stay inside plugin directory") from exc
        return str(candidate)
