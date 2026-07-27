from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, cast

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.utils.helpers import get_local_media_dir
from src.viewmodels.import_questions_agent_viewmodel import (
    ImportQuestionsAgentViewModel,
)
from src.views.components.add_exam_question_dialog import ImageDropArea
from src.views.components.pdf_page_selector_dialog import PdfPageSelectorDialog
from src.views.components.prompt_input_dialog import PromptInputDialog


class PluginFunctionRegistry(Protocol):
    def call_function(
        self, plugin_id: str, function_id: str, payload: Mapping[str, Any]
    ) -> Any:
        ...


class OcrReviewDialog(QDialog):
    def __init__(
        self,
        text: str,
        prompt_factory: Callable[[str], str],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._prompt_factory = prompt_factory
        self.setWindowTitle("Review PaddleOCR Text")
        self.resize(860, 680)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel("Review and edit the OCR text before sending to agent.", self)
        label.setStyleSheet("color: #5f6368;")
        layout.addWidget(label)

        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(text)
        self.text_edit.setMinimumHeight(300)
        layout.addWidget(self.text_edit, 1)

        prompt_label = QLabel("Prompt sent to agent", self)
        prompt_label.setStyleSheet("color: #5f6368;")
        layout.addWidget(prompt_label)

        self.prompt_edit = QTextEdit(self)
        self.prompt_edit.setReadOnly(True)
        self.prompt_edit.setMinimumHeight(220)
        layout.addWidget(self.prompt_edit, 1)

        self.button_box = QDialogButtonBox(self)
        self.save_btn = self.button_box.addButton(
            "Save", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.send_btn = self.button_box.addButton(
            "Save and Send", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.cancel_btn = self.button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.send_btn.setIcon(qta.icon("fa5s.robot", color="#1a73e8"))
        self.save_btn.clicked.connect(self._save_only)
        self.send_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.button_box)
        self.send_after_save = False
        self.text_edit.textChanged.connect(self._refresh_prompt)
        self._refresh_prompt()

    def ocr_text(self) -> str:
        return self.text_edit.toPlainText()

    def _save_only(self) -> None:
        self.send_after_save = False
        self.done(QDialog.DialogCode.Accepted)

    def accept(self) -> None:
        self.send_after_save = True
        super().accept()

    def _refresh_prompt(self) -> None:
        try:
            prompt = self._prompt_factory(self.ocr_text())
        except Exception as exc:
            prompt = str(exc)
        self.prompt_edit.setPlainText(prompt)


class AgentRequestStatusDialog(QDialog):
    def __init__(
        self,
        viewmodel: ImportQuestionsAgentViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setWindowTitle("Agent Requests")
        self.resize(860, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Retry",
                "OCR",
                "Created",
                "Status",
                "Attempts",
                "Parts",
                "Error",
                "ID",
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(7, True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh", self)
        self.check_failed_btn = QPushButton("Check Failed", self)
        self.retry_btn = QPushButton("Retry Checked", self)
        self.remove_btn = QPushButton("Remove", self)
        self.close_btn = QPushButton("Close", self)
        self.check_failed_btn.setIcon(qta.icon("fa5s.check-square", color="#1a73e8"))
        self.retry_btn.setIcon(qta.icon("fa5s.redo", color="#1a73e8"))
        self.remove_btn.setIcon(qta.icon("fa5s.trash", color="#d93025"))
        buttons.addWidget(self.refresh_btn)
        buttons.addWidget(self.check_failed_btn)
        buttons.addWidget(self.retry_btn)
        buttons.addWidget(self.remove_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.refresh_btn.clicked.connect(self.refresh)
        self.check_failed_btn.clicked.connect(self._check_failed_requests)
        self.retry_btn.clicked.connect(self._retry_checked)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.close_btn.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._refresh_buttons)
        self.table.itemChanged.connect(lambda item: self._refresh_buttons())
        self.viewmodel.tasks_changed.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        selected_id = self._selected_task_id()
        checked_ids = set(self._checked_task_ids())
        tasks = self.viewmodel.list_agent_tasks()
        self.table.blockSignals(True)
        self.table.setRowCount(len(tasks))
        selected_row = -1
        for row, task in enumerate(tasks):
            parts = self._parts_text(task.payload)
            created = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
            check_item = QTableWidgetItem("")
            check_item.setData(Qt.ItemDataRole.UserRole, task.id)
            check_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            check_item.setCheckState(
                Qt.CheckState.Checked
                if task.id in checked_ids and task.status != "running"
                else Qt.CheckState.Unchecked
            )
            if task.status == "running":
                check_item.setFlags(Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, check_item)
            ocr_btn = QPushButton("OCR", self.table)
            ocr_btn.setIcon(qta.icon("fa5s.file-alt", color="#1a73e8"))
            ocr_btn.setEnabled(
                task.status != "running" and not self.viewmodel.is_loading
            )
            ocr_btn.clicked.connect(
                lambda checked=False, task_id=task.id: self._review_ocr(task_id)
            )
            self.table.setCellWidget(row, 1, ocr_btn)
            values = [
                created,
                task.status,
                f"{task.attempts}/{task.max_attempts}",
                parts,
                task.error_message,
                task.id,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, task.id)
                self.table.setItem(row, column + 2, item)
            if task.id == selected_id:
                selected_row = row

        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif tasks:
            self.table.selectRow(0)
        self._refresh_buttons()

    def _selected_task_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 7)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""

    def _selected_status(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 3) if row >= 0 else None
        return item.text() if item else ""

    def _refresh_buttons(self) -> None:
        has_selection = bool(self._selected_task_id())
        is_running = self._selected_status() == "running"
        has_checked = bool(self._checked_task_ids())
        self.check_failed_btn.setEnabled(self.table.rowCount() > 0)
        self.retry_btn.setEnabled(has_checked and not self.viewmodel.is_loading)
        self.remove_btn.setEnabled(has_selection and not is_running)

    def _checked_task_ids(self) -> list[str]:
        task_ids: list[str] = []
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            status_item = self.table.item(row, 3)
            id_item = self.table.item(row, 7)
            if (
                check_item is None
                or status_item is None
                or id_item is None
                or check_item.checkState() != Qt.CheckState.Checked
                or status_item.text() == "running"
            ):
                continue
            task_ids.append(str(id_item.data(Qt.ItemDataRole.UserRole) or ""))
        return [task_id for task_id in task_ids if task_id]

    def _check_failed_requests(self) -> None:
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            status_item = self.table.item(row, 3)
            if check_item is None or status_item is None:
                continue
            check_item.setCheckState(
                Qt.CheckState.Checked
                if status_item.text() == "failed"
                else Qt.CheckState.Unchecked
            )
        self.table.blockSignals(False)
        self._refresh_buttons()

    def _retry_checked(self) -> None:
        task_ids = self._checked_task_ids()
        if not task_ids:
            return
        self.viewmodel.retry_agent_tasks(task_ids)
        self.refresh()

    def _remove_selected(self) -> None:
        task_id = self._selected_task_id()
        if not task_id:
            return
        if (
            QMessageBox.question(
                self,
                "Remove Request",
                "Remove the selected agent request?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.viewmodel.remove_agent_task(task_id)
        self.refresh()

    def _review_ocr(self, task_id: str) -> None:
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            text = self.viewmodel.extract_ocr_text_for_task(task_id)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            QMessageBox.critical(self, "PaddleOCR Error", str(exc))
            return
        QApplication.restoreOverrideCursor()
        self.setEnabled(True)

        dialog = OcrReviewDialog(
            text,
            lambda ocr_text, task_id=task_id: self.viewmodel.ocr_prompt_for_task(
                task_id, ocr_text
            ),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        reviewed_text = dialog.ocr_text().strip()
        if not reviewed_text:
            QMessageBox.warning(self, "OCR Text Required", "OCR text is empty.")
            return
        if dialog.send_after_save:
            self.viewmodel.save_task_ocr_text_and_retry(task_id, reviewed_text)
        else:
            self.viewmodel.save_task_ocr_text(task_id, reviewed_text)
        self.refresh()

    def _parts_text(self, payload: dict) -> str:
        parts = []
        for part_payload in payload.get("parts", []) or []:
            if not isinstance(part_payload, dict):
                continue
            question_pages = part_payload.get("question_pages") or []
            transcript_pages = part_payload.get("transcript_pages") or []
            if question_pages or transcript_pages:
                parts.append(f"Part {part_payload.get('part', '?')}")
        return ", ".join(parts) or "-"


class ImportQuestionsAgentDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        viewmodel: Optional[ImportQuestionsAgentViewModel] = None,
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel or ImportQuestionsAgentViewModel(
            agent_content_provider=self._agent_content_from_plugin,
            ocr_text_provider=self._ocr_text_from_plugin,
            parent=self,
        )
        self._part_widgets: dict[int, dict[str, object]] = {}
        self._answer_widgets: dict[str, dict[str, object]] = {}
        self._overall_widgets: dict[str, dict[str, dict[str, object]]] = {}
        self._overall_pdf_paths = {
            section: {"questions": "", "transcripts": ""}
            for section in ("listening", "reading")
        }
        self._overall_source_paths = {
            section: {"questions": "", "transcripts": ""}
            for section in ("listening", "reading")
        }
        self._overall_source_pages: dict[str, dict[str, list[int]]] = {
            section: {"questions": [], "transcripts": []}
            for section in ("listening", "reading")
        }
        self._build_ui()
        self._connect_signals()
        self._refresh_ui()

    def _plugin_registry(self) -> Optional[PluginFunctionRegistry]:
        current = self.parent()
        while current is not None:
            registry = getattr(current, "plugin_ui_registry", None)
            if registry is not None:
                return cast(PluginFunctionRegistry, registry)
            current = current.parent()
        return None

    def _ocr_text_from_plugin(self, payload: dict[str, Any]) -> str:
        registry = self._plugin_registry()
        if registry is None:
            raise ValueError("Plugin services are not available from this window.")
        try:
            result = registry.call_function("ocr", "extract_task_text", payload)
        except KeyError as exc:
            raise ValueError("The OCR plugin is missing or disabled.") from exc
        return str(result)

    def _agent_content_from_plugin(self, payload: dict[str, Any]) -> dict[str, Any]:
        registry = self._plugin_registry()
        if registry is None:
            raise ValueError("Plugin services are not available from this window.")
        try:
            result = registry.call_function("agent", "generate_content", payload)
        except KeyError as exc:
            raise ValueError("The Agent plugin is missing or disabled.") from exc
        if not isinstance(result, dict):
            raise ValueError("The Agent plugin returned an invalid response.")
        return cast(dict[str, Any], result)

    @property
    def result_contexts(self) -> list[dict]:
        return self.viewmodel.result_contexts

    @property
    def result_questions(self) -> list[dict]:
        return self.viewmodel.result_questions

    @property
    def result_answer_key(self) -> dict[int, str]:
        return self.viewmodel.result_answer_key

    def _build_ui(self) -> None:
        self.setWindowTitle("Import Questions Agent")
        self.resize(920, 720)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel("Import Questions Agent", self)
        title.setStyleSheet("font-weight: bold; font-size: 16px; color: #202124;")
        main_layout.addWidget(title)

        self.section_tabs = QTabWidget(self)
        self.section_tabs.addTab(
            self._build_section_tab("listening", [1, 2, 3, 4]),
            "Listening",
        )
        self.section_tabs.addTab(
            self._build_section_tab("reading", [5, 6, 7]),
            "Reading",
        )
        main_layout.addWidget(self.section_tabs, 1)

        self.progress_label = QLabel("", self)
        self.progress_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        main_layout.addWidget(self.progress_label)

        self.button_box = QDialogButtonBox(self)
        self.cancel_btn = self.button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.requests_btn = self.button_box.addButton(
            "Requests", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.requests_btn.setIcon(qta.icon("fa5s.tasks", color="#5f6368"))
        self.send_btn = self.button_box.addButton(
            "Send to agent", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.send_btn.setIcon(qta.icon("fa5s.robot", color="white"))
        self.send_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px;"
        )
        main_layout.addWidget(self.button_box)

    def _build_section_tab(self, section: str, parts: list[int]) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(self._build_steps_area(section, parts), 1)
        return tab

    def _build_steps_area(self, section: str, parts: list[int]) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        steps_container = QWidget(scroll)
        steps_layout = QVBoxLayout(steps_container)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.setSpacing(10)
        steps_layout.addWidget(self._build_answer_sheet_panel(section))
        steps_layout.addWidget(self._build_overall_pdf_panel(section))
        for part in parts:
            steps_layout.addWidget(self._build_part_block(part))
        steps_layout.addStretch(1)
        scroll.setWidget(steps_container)
        return scroll

    def _build_part_block(self, part: int) -> QGroupBox:
        block = QGroupBox(f"Part {part}", self)
        layout = QVBoxLayout(block)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        pdf_group = QGroupBox("PDF page selections", block)
        form = QFormLayout(pdf_group)
        form.setSpacing(8)

        question_label = None
        transcript_label = QLabel("No PDF selected", pdf_group)
        question_button_text = (
            "Select question pages (split 2/page)"
            if part == 1
            else "Select question pages"
        )
        question_button = None
        if part != 2:
            question_label = QLabel("No PDF selected", pdf_group)
            question_button = QPushButton(question_button_text, pdf_group)
            question_button.setIcon(qta.icon("fa5s.file-pdf", color="#ea4335"))
        transcript_button = QPushButton("Select transcript pages", pdf_group)
        transcript_button.setIcon(qta.icon("fa5s.file-alt", color="#5f6368"))

        if question_button is not None and question_label is not None:
            form.addRow(question_button, question_label)
        form.addRow(transcript_button, transcript_label)

        context_edit = QTextEdit(block)
        context_edit.setMinimumHeight(58)
        context_edit.setPlaceholderText("Context text for this part")
        context_edit.setPlainText(self.viewmodel.part_payloads[part].context_text)
        if part == 2:
            form.addRow("Question context:", context_edit)
        else:
            context_edit.hide()

        layout.addWidget(pdf_group)

        prompt_row = QHBoxLayout()
        prompt_label = QLabel("Prompt", block)
        prompt_label.setStyleSheet("color: #5f6368;")
        prompt_button = QPushButton("Edit Prompt", block)
        prompt_button.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        prompt_row.addWidget(prompt_label)
        prompt_row.addStretch(1)
        prompt_row.addWidget(prompt_button)
        layout.addLayout(prompt_row)

        current_prompt = QLabel(self._prompt_preview(part), block)
        current_prompt.setWordWrap(True)
        current_prompt.setStyleSheet(
            "color: #5f6368; border: 1px solid #dadce0; border-radius: 4px; "
            "padding: 6px; background: #fafafa;"
        )
        layout.addWidget(current_prompt)

        self._part_widgets[part] = {
            "question_label": question_label,
            "transcript_label": transcript_label,
            "question_button": question_button,
            "transcript_button": transcript_button,
            "context_edit": context_edit,
            "prompt_label": current_prompt,
            "prompt_button": prompt_button,
        }
        if question_button is not None:
            question_button.clicked.connect(
                lambda checked=False, p=part: self._select_pdf_pages(p, "questions")
            )
        transcript_button.clicked.connect(
            lambda checked=False, p=part: self._select_pdf_pages(p, "transcripts")
        )
        prompt_button.clicked.connect(
            lambda checked=False, p=part: self._edit_part_prompt(p)
        )
        return block

    def _build_answer_sheet_panel(self, section: str) -> QGroupBox:
        panel = QGroupBox("Answer sheet", self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lane = "listening" if section == "listening" else "reading"
        title = (
            "Listening answer sheet"
            if section == "listening"
            else "Reading/Writing answer sheet"
        )
        drop = self._build_answer_drop(title)
        layout.addWidget(drop)

        buttons_row = QHBoxLayout()
        paste_btn = QPushButton(
            "Paste Listening"
            if section == "listening"
            else "Paste Reading/Writing",
            panel,
        )
        paste_btn.setIcon(qta.icon("fa5s.paste", color="#1a73e8"))
        buttons_row.addWidget(paste_btn)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        paste_btn.clicked.connect(lambda: self._paste_answer_sheet(lane))
        shortcut = QShortcut(QKeySequence.StandardKey.Paste, panel)
        shortcut.activated.connect(lambda: self._paste_answer_sheet(lane))
        self._answer_widgets[section] = {
            "drop": drop,
            "paste_button": paste_btn,
            "lane": lane,
        }
        if section == "listening":
            self.listening_drop = drop
            self.paste_listening_btn = paste_btn
        else:
            self.reading_drop = drop
            self.paste_reading_btn = paste_btn
        return panel

    def _build_overall_pdf_panel(self, section: str) -> QGroupBox:
        panel = QGroupBox("Overall PDF Source Files", self)
        form = QFormLayout(panel)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(8)

        questions_label = QLabel("No question source PDF selected", panel)
        transcripts_label = QLabel(
            "No transcript source PDF selected", panel
        )
        questions_btn = QPushButton("Select Question PDF", panel)
        transcripts_btn = QPushButton(
            "Select Transcript PDF", panel
        )
        questions_btn.setIcon(
            qta.icon("fa5s.file-pdf", color="#ea4335")
        )
        transcripts_btn.setIcon(
            qta.icon("fa5s.file-alt", color="#5f6368")
        )
        form.addRow(questions_btn, questions_label)
        form.addRow(transcripts_btn, transcripts_label)

        questions_btn.clicked.connect(
            lambda: self._select_overall_pdf(section, "questions")
        )
        transcripts_btn.clicked.connect(
            lambda: self._select_overall_pdf(section, "transcripts")
        )
        self._overall_widgets[section] = {
            "questions": {
                "label": questions_label,
                "button": questions_btn,
            },
            "transcripts": {
                "label": transcripts_label,
                "button": transcripts_btn,
            },
        }
        return panel

    def _build_answer_drop(self, title: str) -> ImageDropArea:
        drop = ImageDropArea(self)
        drop.setMinimumHeight(120)
        drop.setMaximumHeight(150)
        drop.setText(f"{title}\nDrop image here")
        return drop

    def _connect_signals(self) -> None:
        self.cancel_btn.clicked.connect(self.reject)
        self.requests_btn.clicked.connect(self._show_requests)
        self.send_btn.clicked.connect(self._send_to_agent)
        self.viewmodel.state_changed.connect(self._refresh_ui)
        self.viewmodel.tasks_changed.connect(self._refresh_ui)
        self.viewmodel.progress_message.connect(self._show_progress)
        self.viewmodel.error_message.connect(self._show_error)
        self.viewmodel.import_ready.connect(self.accept)

    def _select_pdf_pages(self, part: int, lane: str) -> None:
        section = self._section_for_part(part)
        pdf_path = self._overall_pdf_paths[section].get(lane, "")
        if not pdf_path:
            QMessageBox.warning(
                self,
                "Source PDF Required",
                "Create the overall source PDF before selecting part pages.",
            )
            return

        allowed_parts = self._parts_for_section(section)
        if lane == "questions":
            allowed_parts = [
                target_part for target_part in allowed_parts if target_part != 2
            ]
        selected_pages_by_part = self._current_pages_by_part(
            pdf_path, lane, part, allowed_parts
        )
        selected_pages = selected_pages_by_part.get(part, [])
        lane_label = "question pages" if lane == "questions" else "transcript pages"
        action_text = (
            "Save question pages" if lane == "questions" else "Save transcript pages"
        )
        dialog = PdfPageSelectorDialog(
            pdf_path,
            selected_pages,
            self,
            action_text=action_text,
            initial_part=part,
            selected_pages_by_part=selected_pages_by_part,
            lane_label=lane_label,
            allowed_parts=allowed_parts,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for target_part, page_indices in dialog.selected_pages_by_part.items():
            if target_part == 2 and lane == "questions":
                continue
            if page_indices:
                self.viewmodel.set_part_pdf(target_part, lane, pdf_path, page_indices)
        self._refresh_ui()

    def _select_overall_pdf(self, section: str, lane: str) -> None:
        current_path = self._overall_source_paths[section].get(lane, "")
        start_dir = str(Path(current_path).parent) if current_path else ""
        title = (
            f"Select {section.title()} Question PDF"
            if lane == "questions"
            else f"Select {section.title()} Transcript PDF"
        )
        pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            start_dir,
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not pdf_path:
            return

        selected_pages = []
        if self._overall_source_paths[section].get(lane) == pdf_path:
            selected_pages = list(self._overall_source_pages[section].get(lane, []))
        action_text = (
            f"Create {section} question source PDF"
            if lane == "questions"
            else f"Create {section} transcript source PDF"
        )
        dialog = PdfPageSelectorDialog(
            pdf_path,
            selected_pages,
            self,
            action_text=action_text,
            lane_label="source pages",
            allow_part_assignment=False,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        target_name = f"temp_{section}_{lane}_pdf.pdf"
        target_path = get_local_media_dir() / target_name
        try:
            self._extract_pdf_pages(pdf_path, dialog.selected_pages, target_path)
        except Exception as exc:
            QMessageBox.critical(self, "PDF Error", str(exc))
            return

        self._overall_source_paths[section][lane] = pdf_path
        self._overall_source_pages[section][lane] = list(dialog.selected_pages)
        self._overall_pdf_paths[section][lane] = str(target_path)
        self._sync_part_source_pdf(section, lane, str(target_path))
        self._refresh_ui()

    def _extract_pdf_pages(
        self, pdf_path: str, page_indices: list[int], target_path: Path
    ) -> None:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise ImportError("pypdf is required for PDF page extraction.") from exc

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        page_count = len(reader.pages)
        for page_index in sorted(set(page_indices)):
            if page_index < 0 or page_index >= page_count:
                raise ValueError(
                    f"Page {page_index + 1} is outside {Path(pdf_path).name}."
                )
            writer.add_page(reader.pages[page_index])
        if not writer.pages:
            raise ValueError("Select at least one page.")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as handle:
            writer.write(handle)

    def _sync_part_source_pdf(self, section: str, lane: str, pdf_path: str) -> None:
        for part in self._parts_for_section(section):
            if part == 2 and lane == "questions":
                continue
            self.viewmodel.set_part_pdf(part, lane, pdf_path, [])

    def _current_pages_by_part(
        self,
        pdf_path: str,
        lane: str,
        default_part: int,
        allowed_parts: list[int],
    ) -> dict[int, list[int]]:
        pages_by_part: dict[int, list[int]] = {}
        for part in allowed_parts:
            current_path = self._current_pdf_path(part, lane)
            if current_path and Path(current_path) != Path(pdf_path):
                continue
            pages = self._current_pages(part, lane)
            if pages:
                pages_by_part[part] = list(pages)

        if default_part in allowed_parts and default_part not in pages_by_part:
            pages_by_part[default_part] = list(self._current_pages(default_part, lane))
        return pages_by_part

    def _current_pdf_path(self, part: int, lane: str) -> str:
        payload = self.viewmodel.part_payloads[part]
        if lane == "questions":
            return payload.question_pdf_path
        return payload.transcript_pdf_path

    def _current_pages(self, part: int, lane: str) -> list[int]:
        payload = self.viewmodel.part_payloads[part]
        if lane == "questions":
            return payload.question_pages
        return payload.transcript_pages

    def _paste_answer_sheet(self, lane: str) -> None:
        drop_area = self.listening_drop if lane == "listening" else self.reading_drop
        if not drop_area.paste_from_clipboard():
            QMessageBox.warning(
                self, "No Image", "Clipboard does not contain an image."
            )
            return
        self.viewmodel.set_answer_sheet_image(lane, drop_area.image_path)

    def _send_to_agent(self) -> None:
        for part, widgets in self._part_widgets.items():
            context_edit = widgets["context_edit"]
            if isinstance(context_edit, QTextEdit):
                self.viewmodel.set_part_context_text(part, context_edit.toPlainText())

        for section, widgets in self._answer_widgets.items():
            drop = widgets["drop"]
            lane = widgets["lane"]
            if isinstance(drop, ImageDropArea) and isinstance(lane, str):
                if drop.image_path:
                    self.viewmodel.set_answer_sheet_image(lane, drop.image_path)
        self.viewmodel.send_to_agent()

    def _refresh_ui(self) -> None:
        for section, lanes in self._overall_widgets.items():
            for lane, widgets in lanes.items():
                label = widgets["label"]
                if isinstance(label, QLabel):
                    label.setText(self._overall_pdf_summary(section, lane))
        for part, widgets in self._part_widgets.items():
            question_label = widgets["question_label"]
            transcript_label = widgets["transcript_label"]
            prompt_label = widgets["prompt_label"]
            if isinstance(question_label, QLabel):
                question_label.setText(self.viewmodel.pdf_summary(part, "questions"))
            if isinstance(transcript_label, QLabel):
                transcript_label.setText(
                    self.viewmodel.pdf_summary(part, "transcripts")
                )
            if isinstance(prompt_label, QLabel):
                prompt_label.setText(self._prompt_preview(part))

        self.send_btn.setEnabled(self.viewmodel.can_send())
        self.cancel_btn.setEnabled(not self.viewmodel.is_loading)
        self.requests_btn.setEnabled(True)
        for part, widgets in self._part_widgets.items():
            section = self._section_for_part(part)
            for key, lane in (
                ("question_button", "questions"),
                ("transcript_button", "transcripts"),
            ):
                button = widgets[key]
                if isinstance(button, QPushButton):
                    button.setEnabled(
                        not self.viewmodel.is_loading
                        and bool(self._overall_pdf_paths[section].get(lane))
                    )
        for widgets in self._answer_widgets.values():
            button = widgets["paste_button"]
            if isinstance(button, QPushButton):
                button.setEnabled(not self.viewmodel.is_loading)
        for lanes in self._overall_widgets.values():
            for widgets in lanes.values():
                button = widgets["button"]
                if isinstance(button, QPushButton):
                    button.setEnabled(not self.viewmodel.is_loading)
        if self.viewmodel.is_loading:
            self.send_btn.setText("Sending...")
        else:
            self.send_btn.setText("Send to agent")

    def _overall_pdf_summary(self, section: str, lane: str) -> str:
        source_path = self._overall_source_paths[section].get(lane, "")
        temp_path = self._overall_pdf_paths[section].get(lane, "")
        if not source_path or not temp_path:
            return (
                "No question source PDF selected"
                if lane == "questions"
                else "No transcript source PDF selected"
            )
        pages = ", ".join(
            str(index + 1)
            for index in self._overall_source_pages[section].get(lane, [])
        )
        return f"{Path(source_path).name}: pages {pages} -> {Path(temp_path).name}"

    def _section_for_part(self, part: int) -> str:
        return "listening" if part in (1, 2, 3, 4) else "reading"

    def _parts_for_section(self, section: str) -> list[int]:
        if section == "listening":
            return [1, 2, 3, 4]
        return [5, 6, 7]

    def _prompt_preview(self, part: int) -> str:
        prompt = self.viewmodel.part_payloads[part].prompt.strip()
        if not prompt:
            return "Prompt is empty"
        single_line = " ".join(prompt.split())
        if len(single_line) <= 220:
            return single_line
        return f"{single_line[:220]}..."

    def _edit_part_prompt(self, part: int) -> None:
        dialog = PromptInputDialog(
            self.viewmodel.part_payloads[part].prompt,
            self,
            title=f"Edit Part {part} Prompt",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.viewmodel.set_part_prompt(part, dialog.prompt_text())
        self._refresh_ui()

    def _show_progress(self, message: str) -> None:
        self.progress_label.setText(message)

    def _show_requests(self) -> None:
        dialog = AgentRequestStatusDialog(self.viewmodel, self)
        dialog.exec()

    def _show_error(self, message: str) -> None:
        print(message)
        QMessageBox.critical(self, "Agent Import Error", message)
