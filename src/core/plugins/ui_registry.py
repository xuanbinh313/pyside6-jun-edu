"""Dynamic UI contribution registry used by plugins and MainWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class UIActionContribution:
    """A menu, toolbar, or context-menu action contributed by a plugin."""

    plugin_id: str
    action_id: str
    title: str
    location: str
    callback: Callable[[], None]
    icon: QIcon


@dataclass(frozen=True)
class UIPageContribution:
    """A stack page contributed by a plugin."""

    plugin_id: str
    page_id: str
    title: str
    widget_factory: Callable[[], QWidget]


PluginFunction = Callable[[Mapping[str, Any]], Any]


class UIRegistry(QObject):
    """Store plugin UI contributions and notify the application shell."""

    action_registered = Signal(object)
    page_registered = Signal(object)
    plugin_unregistered = Signal(str)
    page_requested = Signal(str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._actions: Dict[Tuple[str, str], UIActionContribution] = {}
        self._pages: Dict[Tuple[str, str], UIPageContribution] = {}
        self._functions: Dict[Tuple[str, str], PluginFunction] = {}

    def register_action(
        self,
        plugin_id: str,
        action_id: str,
        title: str,
        location: str,
        callback: Callable[[], None],
        icon: Optional[QIcon] = None,
    ) -> None:
        """Register a plugin action contribution."""
        contribution = UIActionContribution(
            plugin_id=plugin_id,
            action_id=action_id,
            title=title,
            location=location,
            callback=callback,
            icon=icon if icon is not None else QIcon(),
        )
        self._actions[(plugin_id, action_id)] = contribution
        self.action_registered.emit(contribution)

    def register_page(
        self,
        plugin_id: str,
        page_id: str,
        title: str,
        widget_factory: Callable[[], QWidget],
    ) -> None:
        """Register a plugin stack page contribution."""
        contribution = UIPageContribution(
            plugin_id=plugin_id,
            page_id=page_id,
            title=title,
            widget_factory=widget_factory,
        )
        self._pages[(plugin_id, page_id)] = contribution
        self.page_registered.emit(contribution)

    def request_page(self, plugin_id: str, page_id: str) -> None:
        """Ask the application shell to show a registered plugin page."""
        self.page_requested.emit(plugin_id, page_id)

    def get_page(self, plugin_id: str, page_id: str) -> UIPageContribution:
        """Return a registered plugin page."""
        return self._pages[(plugin_id, page_id)]

    def register_function(
        self, plugin_id: str, function_id: str, callback: PluginFunction
    ) -> None:
        """Register a callable plugin function for non-UI app code."""
        self._functions[(plugin_id, function_id)] = callback

    def get_function(self, plugin_id: str, function_id: str) -> PluginFunction:
        """Return a registered plugin function."""
        return self._functions[(plugin_id, function_id)]

    def call_function(
        self, plugin_id: str, function_id: str, payload: Mapping[str, Any]
    ) -> Any:
        """Call a registered plugin function and return its result."""
        return self.get_function(plugin_id, function_id)(payload)

    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove all UI contributions for a plugin."""
        self._actions = {
            key: action
            for key, action in self._actions.items()
            if action.plugin_id != plugin_id
        }
        self._pages = {
            key: page for key, page in self._pages.items() if page.plugin_id != plugin_id
        }
        self._functions = {
            key: callback
            for key, callback in self._functions.items()
            if key[0] != plugin_id
        }
        self.plugin_unregistered.emit(plugin_id)
