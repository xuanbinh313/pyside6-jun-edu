"""Contracts implemented by in-process Jun Edu plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.plugins.plugin_context import PluginContext


class JunEduPlugin(ABC):
    """Base class for plugin entry objects."""

    plugin_id: str

    @abstractmethod
    def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin and register UI contributions."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release plugin resources before application exit."""


class PluginFactory(Protocol):
    """Callable contract exported by plugin modules as create_plugin."""

    def __call__(self) -> JunEduPlugin:
        """Create a plugin instance."""
