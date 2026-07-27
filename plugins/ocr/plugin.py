"""OCR plugin adapter for Jun Edu."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

import qtawesome as qta
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from src.core.plugins.exceptions import WorkerError
from src.core.plugins.plugin_base import JunEduPlugin
from src.core.plugins.plugin_context import PluginContext
from src.core.plugins.plugin_worker import PluginWorker


class OcrPlugin(JunEduPlugin):
    plugin_id = "ocr"

    def __init__(self) -> None:
        self._context: Optional[PluginContext] = None

    def initialize(self, context: PluginContext) -> None:
        self._context = context
        context.ui.register_function(
            self.plugin_id,
            "extract_task_text",
            self.extract_task_text,
        )
        context.ui.register_page(
            self.plugin_id,
            "dashboard",
            "OCR",
            self._create_page,
        )
        context.ui.register_action(
            self.plugin_id,
            "open",
            "OCR",
            "menu,toolbar",
            lambda: context.ui.request_page(self.plugin_id, "dashboard"),
            qta.icon("fa5s.file-image", color="#1a73e8"),
        )

    def shutdown(self) -> None:
        self._context = None

    def _create_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("OCR")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        status = QLabel("OCR worker is not running. Start it only when OCR is needed.")
        status.setWordWrap(True)
        start_button = QPushButton("Check OCR Worker")
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
            status.setText("OCR worker is running.")
        else:
            status.setText(f"OCR worker is ready for lazy startup: {self._worker_path()}")

    def extract_task_text(self, payload: Mapping[str, Any]) -> str:
        """Call the out-of-process OCR worker."""
        response = self._worker().send_request(
            {
                "method": "extract_task_text",
                "payload": dict(payload),
            }
        )
        if not response.get("ok", False):
            raise WorkerError(str(response.get("error") or "OCR worker failed."))
        result = response.get("result", "")
        return str(result)

    def _worker(self) -> PluginWorker:
        context = self._context
        if context is None:
            raise WorkerError("OCR plugin is not initialized.")
        worker_path = self._worker_path()
        return context.workers.get_worker(
            self.plugin_id,
            "ocr",
            worker_path,
            cwd=worker_path.parent,
        )

    def _worker_path(self) -> Path:
        context = self._context
        if context is None:
            raise WorkerError("OCR plugin is not initialized.")
        return Path(context.get_resource_path("workers/ocr-worker.exe"))


def create_plugin() -> JunEduPlugin:
    return OcrPlugin()
