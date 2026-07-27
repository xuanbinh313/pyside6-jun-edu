"""Parsing and validation for plugin.json files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.core.plugins.exceptions import PluginManifestError

_PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*$")
_VALID_EXECUTION_MODES = {"in_process", "process"}


@dataclass(frozen=True)
class PluginManifest:
    """Validated plugin manifest data."""

    plugin_id: str
    name: str
    version: str
    api_version: str
    entry: str
    enabled: bool
    execution: str

    @classmethod
    def load(cls, manifest_path: Path) -> "PluginManifest":
        """Load and validate a plugin manifest from disk."""
        if not manifest_path.is_file():
            raise PluginManifestError(f"Missing manifest: {manifest_path}")

        try:
            raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PluginManifestError(f"Invalid JSON in {manifest_path}: {exc}") from exc

        if not isinstance(raw_data, Mapping):
            raise PluginManifestError("Plugin manifest must be a JSON object")

        manifest = cls.from_mapping(raw_data)
        manifest._validate_entry_path(manifest_path.parent)
        return manifest

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PluginManifest":
        """Create a manifest from parsed JSON data."""
        plugin_id = _require_str(data, "id")
        name = _require_str(data, "name")
        version = _require_str(data, "version")
        api_version = _require_str(data, "api_version")
        entry = _require_str(data, "entry")
        enabled = _require_bool(data, "enabled")
        execution = _require_str(data, "execution")

        if _PLUGIN_ID_PATTERN.fullmatch(plugin_id) is None:
            raise PluginManifestError(
                "Plugin id must start with a lowercase letter and contain only "
                "lowercase letters, numbers, underscores, dots, or hyphens"
            )
        if execution not in _VALID_EXECUTION_MODES:
            raise PluginManifestError(
                f"Plugin execution must be one of: {', '.join(sorted(_VALID_EXECUTION_MODES))}"
            )

        return cls(
            plugin_id=plugin_id,
            name=name,
            version=version,
            api_version=api_version,
            entry=entry,
            enabled=enabled,
            execution=execution,
        )

    def _validate_entry_path(self, plugin_dir: Path) -> None:
        entry_path = (plugin_dir / self.entry).resolve()
        plugin_root = plugin_dir.resolve()
        try:
            entry_path.relative_to(plugin_root)
        except ValueError as exc:
            raise PluginManifestError("Plugin entry must stay inside plugin directory") from exc
        if not entry_path.is_file():
            raise PluginManifestError(f"Plugin entry does not exist: {entry_path}")


def _require_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PluginManifestError(f"Plugin manifest field '{key}' must be a non-empty string")
    if ".." in Path(value).parts:
        raise PluginManifestError(f"Plugin manifest field '{key}' cannot contain '..'")
    return value


def _require_bool(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise PluginManifestError(f"Plugin manifest field '{key}' must be a boolean")
    return value
