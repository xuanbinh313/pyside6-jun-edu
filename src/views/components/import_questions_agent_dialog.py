from __future__ import annotations
from src.viewmodels.import_questions_agent_viewmodel import (
    ImportQuestionsAgentViewModel,
)
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


from src.views.components.add_exam_question_dialog import ImageDropArea
from src.views.components.pdf_page_selector_dialog import PdfPageSelectorDialog


class AgentRequestStatusDialog(QDialog):
    def __init__(self, viewmodel: ImportQuestionsAgentViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setWindowTitle("Agent Requests")
        self.resize(860, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Created", "Status", "Attempts", "Parts", "Error", "ID"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(5, True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh", self)
        self.retry_btn = QPushButton("Retry", self)
        self.remove_btn = QPushButton("Remove", self)
        self.close_btn = QPushButton("Close", self)
        self.retry_btn.setIcon(qta.icon("fa5s.redo", color="#1a73e8"))
        self.remove_btn.setIcon(qta.icon("fa5s.trash", color="#d93025"))
        buttons.addWidget(self.refresh_btn)
        buttons.addWidget(self.retry_btn)
        buttons.addWidget(self.remove_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.refresh_btn.clicked.connect(self.refresh)
        self.retry_btn.clicked.connect(self._retry_selected)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.close_btn.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._refresh_buttons)
        self.viewmodel.tasks_changed.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        selected_id = self._selected_task_id()
        tasks = self.viewmodel.list_agent_tasks()
        self.table.setRowCount(len(tasks))
        selected_row = -1
        for row, task in enumerate(tasks):
            parts = self._parts_text(task.payload)
            created = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
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
                self.table.setItem(row, column, item)
            if task.id == selected_id:
                selected_row = row

        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif tasks:
            self.table.selectRow(0)
        self._refresh_buttons()

    def _selected_task_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""

    def _selected_status(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 1) if row >= 0 else None
        return item.text() if item else ""

    def _refresh_buttons(self) -> None:
        has_selection = bool(self._selected_task_id())
        is_running = self._selected_status() == "running"
        self.retry_btn.setEnabled(has_selection and not is_running)
        self.remove_btn.setEnabled(has_selection and not is_running)

    def _retry_selected(self) -> None:
        task_id = self._selected_task_id()
        if task_id:
            self.viewmodel.retry_agent_task(task_id)
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
        parent=None,
        viewmodel: ImportQuestionsAgentViewModel | None = None,
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel or ImportQuestionsAgentViewModel(parent=self)
        self._part_widgets: dict[int, dict[str, object]] = {}
        self._build_ui()
        self._connect_signals()
        self._refresh_ui()

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

        main_layout.addWidget(self._build_answer_sheet_panel())

        self.tabs = QTabWidget(self)
        for part in self.viewmodel.TOEIC_PARTS:
            self.tabs.addTab(self._build_part_tab(part), f"Part {part}")
        main_layout.addWidget(self.tabs, 1)

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

    def _build_part_tab(self, part: int) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        pdf_group = QGroupBox("PDF page selections", tab)
        form = QFormLayout(pdf_group)
        form.setSpacing(8)

        question_label = QLabel("No PDF selected", pdf_group)
        transcript_label = QLabel("No PDF selected", pdf_group)
        question_button_text = (
            "Select question pages (split 2/page)"
            if part == 1
            else "Select question pages"
        )
        question_button = QPushButton(question_button_text, pdf_group)
        transcript_button = QPushButton("Select transcript pages", pdf_group)
        question_button.setIcon(qta.icon("fa5s.file-pdf", color="#ea4335"))
        transcript_button.setIcon(qta.icon("fa5s.file-alt", color="#5f6368"))

        if part != 2:
            form.addRow(question_button, question_label)
        form.addRow(transcript_button, transcript_label)
        layout.addWidget(pdf_group)

        context_edit = QTextEdit(tab)
        context_edit.setMinimumHeight(58)
        context_edit.setPlaceholderText("Context text for this part")
        context_edit.setPlainText(self.viewmodel.part_payloads[part].context_text)
        if part == 2:
            form.addRow("Question context:", context_edit)
        else:
            context_edit.hide()

        prompt_edit = QTextEdit(tab)
        prompt_edit.setMinimumHeight(250)
        prompt_edit.setPlainText(self.viewmodel.part_payloads[part].prompt)
        prompt_edit.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; "
            "font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(QLabel("Prompt", tab))
        layout.addWidget(prompt_edit, 1)

        self._part_widgets[part] = {
            "question_label": question_label,
            "transcript_label": transcript_label,
            "question_button": question_button,
            "transcript_button": transcript_button,
            "context_edit": context_edit,
            "prompt_edit": prompt_edit,
        }
        if part != 2:
            question_button.clicked.connect(
                lambda checked=False, p=part: self._select_pdf_pages(p, "questions")
            )
        transcript_button.clicked.connect(
            lambda checked=False, p=part: self._select_pdf_pages(p, "transcripts")
        )
        return tab

    def _build_answer_sheet_panel(self) -> QGroupBox:
        panel = QGroupBox("Answer sheets", self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        images_row = QHBoxLayout()
        self.listening_drop = self._build_answer_drop("Listening answer sheet")
        self.reading_drop = self._build_answer_drop("Reading/Writing answer sheet")
        images_row.addWidget(self.listening_drop)
        images_row.addWidget(self.reading_drop)
        layout.addLayout(images_row)

        buttons_row = QHBoxLayout()
        self.paste_listening_btn = QPushButton("Paste Listening", panel)
        self.paste_reading_btn = QPushButton("Paste Reading/Writing", panel)
        self.paste_listening_btn.setIcon(qta.icon("fa5s.paste", color="#1a73e8"))
        self.paste_reading_btn.setIcon(qta.icon("fa5s.paste", color="#1a73e8"))
        buttons_row.addWidget(self.paste_listening_btn)
        buttons_row.addWidget(self.paste_reading_btn)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        self.paste_listening_btn.clicked.connect(
            lambda: self._paste_answer_sheet("listening")
        )
        self.paste_reading_btn.clicked.connect(
            lambda: self._paste_answer_sheet("reading")
        )
        shortcut = QShortcut(QKeySequence.StandardKey.Paste, panel)
        shortcut.activated.connect(lambda: self._paste_answer_sheet("listening"))
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
        current_path = self._current_pdf_path(part, lane)
        start_dir = str(Path(current_path).parent) if current_path else ""
        pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF",
            start_dir,
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not pdf_path:
            return

        selected_pages_by_part = self._current_pages_by_part(pdf_path, lane, part)
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
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for target_part, page_indices in dialog.selected_pages_by_part.items():
            if target_part == 2 and lane == "questions":
                continue
            if page_indices:
                self.viewmodel.set_part_pdf(target_part, lane, pdf_path, page_indices)

    def _current_pages_by_part(
        self, pdf_path: str, lane: str, default_part: int
    ) -> dict[int, list[int]]:
        pages_by_part: dict[int, list[int]] = {}
        for part in self.viewmodel.TOEIC_PARTS:
            current_path = self._current_pdf_path(part, lane)
            if current_path and Path(current_path) != Path(pdf_path):
                continue
            pages = self._current_pages(part, lane)
            if pages:
                pages_by_part[part] = list(pages)

        if default_part not in pages_by_part:
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
            prompt_edit = widgets["prompt_edit"]
            context_edit = widgets["context_edit"]
            if isinstance(prompt_edit, QTextEdit):
                self.viewmodel.set_part_prompt(part, prompt_edit.toPlainText())
            if isinstance(context_edit, QTextEdit):
                self.viewmodel.set_part_context_text(part, context_edit.toPlainText())

        if self.listening_drop.image_path:
            self.viewmodel.set_answer_sheet_image(
                "listening", self.listening_drop.image_path
            )
        if self.reading_drop.image_path:
            self.viewmodel.set_answer_sheet_image(
                "reading", self.reading_drop.image_path
            )
        self.viewmodel.send_to_agent()

    def _refresh_ui(self) -> None:
        for part, widgets in self._part_widgets.items():
            question_label = widgets["question_label"]
            transcript_label = widgets["transcript_label"]
            if isinstance(question_label, QLabel):
                question_label.setText(self.viewmodel.pdf_summary(part, "questions"))
            if isinstance(transcript_label, QLabel):
                transcript_label.setText(
                    self.viewmodel.pdf_summary(part, "transcripts")
                )

        self.send_btn.setEnabled(self.viewmodel.can_send())
        self.cancel_btn.setEnabled(not self.viewmodel.is_loading)
        self.requests_btn.setEnabled(True)
        for widgets in self._part_widgets.values():
            for key in ("question_button", "transcript_button"):
                button = widgets[key]
                if isinstance(button, QPushButton):
                    button.setEnabled(not self.viewmodel.is_loading)
        self.paste_listening_btn.setEnabled(not self.viewmodel.is_loading)
        self.paste_reading_btn.setEnabled(not self.viewmodel.is_loading)
        if self.viewmodel.is_loading:
            self.send_btn.setText("Sending...")
        else:
            self.send_btn.setText("Send to agent")

    def _show_progress(self, message: str) -> None:
        self.progress_label.setText(message)

    def _show_requests(self) -> None:
        dialog = AgentRequestStatusDialog(self.viewmodel, self)
        dialog.exec()

    def _show_error(self, message: str) -> None:
        print(message)
        QMessageBox.critical(self, "Agent Import Error", message)
