"""Agent plugin adapter for Jun Edu."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

import qtawesome as qta
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from src.core.plugins.exceptions import WorkerError
from src.core.plugins.plugin_base import JunEduPlugin
from src.core.plugins.plugin_context import PluginContext
from src.core.plugins.plugin_worker import PluginWorker


class AgentPlugin(JunEduPlugin):
    plugin_id = "agent"

    def __init__(self) -> None:
        self._context: Optional[PluginContext] = None

    def initialize(self, context: PluginContext) -> None:
        self._context = context
        context.ui.register_function(
            self.plugin_id,
            "generate_content",
            self.generate_content,
        )
        context.ui.register_page(
            self.plugin_id,
            "dashboard",
            "Agent",
            self._create_page,
        )
        context.ui.register_action(
            self.plugin_id,
            "open",
            "Agent",
            "menu,toolbar",
            lambda: context.ui.request_page(self.plugin_id, "dashboard"),
            qta.icon("fa5s.robot", color="#1a73e8"),
        )

    def shutdown(self) -> None:
        self._context = None

    def _create_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Agent")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        status = QLabel("Agent worker is not running. Start it only when an agent task is requested.")
        status.setWordWrap(True)
        start_button = QPushButton("Check Agent Worker")
        start_button.clicked.connect(lambda: self._check_worker(status))

        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(start_button)
        layout.addStretch(1)
        return page

    def _check_worker(self, status: QLabel) -> None:
        try:
            worker = self._worker()
        except WorkerError as exc:
            status.setText(str(exc))
            return
        if worker.is_running:
            status.setText("Agent worker is running.")
        else:
            status.setText(
                f"Agent worker is ready for lazy startup: {self._worker_path()}"
            )

    def generate_content(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Call the out-of-process agent worker."""
        worker_payload = dict(payload)
        response_schema = worker_payload.pop("response_schema", None)
        if response_schema is not None:
            worker_payload["response_schema_name"] = getattr(
                response_schema, "__name__", str(response_schema)
            )
        response = self._worker().send_request(
            {
                "method": "generate_content",
                "payload": worker_payload,
            }
        )
        if not response.get("ok", False):
            raise WorkerError(str(response.get("error") or "Agent worker failed."))
        result = response.get("result")
        if not isinstance(result, dict):
            raise WorkerError("Agent worker returned an invalid response.")
        return {str(key): value for key, value in result.items()}

    def _worker(self) -> PluginWorker:
        context = self._context
        if context is None:
            raise WorkerError("Agent plugin is not initialized.")
        worker_path = self._worker_path()
        return context.workers.get_worker(
            self.plugin_id,
            "agent",
            worker_path,
            cwd=worker_path.parent,
        )

    def _worker_path(self) -> Path:
        context = self._context
        if context is None:
            raise WorkerError("Agent plugin is not initialized.")
        return Path(context.get_resource_path("workers/agent-worker.exe"))


def create_plugin() -> JunEduPlugin:
    return AgentPlugin()
