from shiboken6 import isValid
import html
import json

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QRadioButton,
    QWidget,
)

from src.repositories.sqlite.database import get_session
from src.views.components.tag_menu_dialog import TagMenuDialog
from ui_gen.ui_option_question_item import Ui_OptionQuestionItem
from src.repositories.sqlite import orm_models as exam_model


class OptionQuestionItem(QWidget):
    """Renders multiple-choice options for one ExamQuestion."""

    LETTER_MAP = ["A", "B", "C", "D"]

    def __init__(self, question, exam_id=None, parent=None):
        super().__init__(parent)
        self.question = question
        self.exam_id = exam_id
        self.correct_answer = question.correct_answer
        try:
            self.orig_correct_idx = self.LETTER_MAP.index(self.correct_answer)
        except ValueError:
            self.orig_correct_idx = -1
        self.display_correct_letter = ""
        self._build(question)

    def _build(self, q):
        self.ui = Ui_OptionQuestionItem()
        self.ui.setupUi(self)

        self.tags_label = QLabel(self)
        self.tags_label.setTextFormat(Qt.TextFormat.PlainText)
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-size: 11px;
                font-weight: bold;
                padding: 0 4px 2px 4px;
            }
        """)
        self.ui.main_layout.insertWidget(0, self.tags_label)

        self.ui.stem.setText(f"<b>Q{q.question_number}.</b> {q.content}")
        self.ui.stem.setStyleSheet("font-size: 13px; color: #202124; padding: 4px 0;")
        self.ui.header_layout.setStretchFactor(self.ui.stem, 1)

        icon_btn_style = """
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                border-radius: 12px;
            }
        """

        self.ui.edit_q_btn.setVisible(False)

        self.ui.tag_btn.setIcon(qta.icon("fa5s.tags", color="#5f6368"))
        self.ui.tag_btn.setToolTip("Manage tags for this question")
        self.ui.tag_btn.setFixedSize(24, 24)
        self.ui.tag_btn.setStyleSheet(icon_btn_style)
        self.ui.tag_btn.clicked.connect(self._show_tag_menu)
        self._refresh_tag_ui()

        self.ui.header_layout.removeWidget(self.ui.select_audio_btn)
        self.ui.select_audio_btn.setParent(None)
        self.ui.select_audio_btn.deleteLater()

        try:
            raw_opts = (
                json.loads(q.options)
                if isinstance(q.options, str)
                else (q.options or [])
            )
        except Exception:
            raw_opts = []

        indexed = list(enumerate(raw_opts))
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for display_pos, (orig_idx, opt_text) in enumerate(indexed):
            display_letter = (
                self.LETTER_MAP[display_pos] if display_pos < 4 else str(display_pos)
            )
            if orig_idx == self.orig_correct_idx:
                self.display_correct_letter = display_letter

            radio = QRadioButton(f"{display_letter}.  {opt_text}")
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 12px;
                    color: #3c4043;
                    padding: 3px 6px;
                }
                QRadioButton:hover { color: #1a73e8; }
            """)
            radio.setProperty("orig_idx", orig_idx)
            self.btn_group.addButton(radio, display_pos)
            self.ui.options_layout.addWidget(radio)

        self._result_label = self.ui.result_label
        self._result_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding: 2px 6px;"
        )
        self._result_label.setWordWrap(True)

        self.ui.check_btn.setFixedWidth(130)
        self.ui.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        self.ui.check_btn.clicked.connect(self._on_check)

    def _feedback_text(self, summary: str) -> str:
        note = self._answer_note()
        if not note:
            return html.escape(summary)
        safe_note = html.escape(note).replace("\n", "<br>")
        return (
            f"{html.escape(summary)}<br>"
            f'<span style="font-weight:normal; color:#3c4043;">'
            f"Note: {safe_note}</span>"
        )

    def _answer_note(self) -> str:
        meta = (
            self.question.additional_meta
            if isinstance(self.question.additional_meta, dict)
            else {}
        )
        return str(meta.get("note", "")).strip()

    def _on_check(self):
        selected = self.btn_group.checkedButton()
        if not selected:
            self._result_label.setText("Please select an option first.")
            self._result_label.setStyleSheet(
                "color: #f9ab00; font-weight: bold; font-size: 12px;"
            )
            return

        orig_idx = selected.property("orig_idx")
        if orig_idx == self.orig_correct_idx:
            self._result_label.setText(self._feedback_text("Correct!"))
            self._result_label.setStyleSheet(
                "color: #34a853; font-weight: bold; font-size: 12px;"
            )
        else:
            self._result_label.setText(
                self._feedback_text(
                    f"Wrong. Correct answer: {self.display_correct_letter}"
                )
            )
            self._result_label.setStyleSheet(
                "color: #ea4335; font-weight: bold; font-size: 12px;"
            )
        self._notify_question_checked()

    def _notify_question_checked(self):
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_checked"):
                parent_widget.on_question_checked(self.question)
                break
            parent_widget = parent_widget.parent()

    def _is_alive(self):
        return (
            isValid(self)
            and hasattr(self, "ui")
            and hasattr(self.ui, "tag_btn")
            and isValid(self.ui.tag_btn)
            and hasattr(self, "tags_label")
            and isValid(self.tags_label)
        )

    def _show_tag_menu(self):
        if not self._is_alive():
            return

        popup = TagMenuDialog(self.question, self)

        pos = self.ui.tag_btn.mapToGlobal(QPoint(0, self.ui.tag_btn.height()))
        popup.move(pos)

        popup.exec()

        if self._is_alive():
            self._refresh_tag_ui()

    def _tag_names(self):
        session = get_session()
        try:
            rows = (
                session.query(exam_model.UserQuestionTag.tag_name)
                .filter(
                    exam_model.UserQuestionTag.question_id == self.question.id,
                )
                .order_by(exam_model.UserQuestionTag.tag_name.asc())
                .all()
            )
            return [row[0] for row in rows]
        finally:
            session.close()

    def _refresh_tag_ui(self):
        if not self._is_alive():
            return

        tag_names = self._tag_names()
        has_tags = bool(tag_names)

        color = "#1a73e8" if has_tags else "#5f6368"
        tooltip = (
            "Tagged: " + ", ".join(tag_names)
            if has_tags
            else "Manage tags for this question"
        )

        self.ui.tag_btn.setIcon(qta.icon("fa5s.tags", color=color))
        self.ui.tag_btn.setToolTip(tooltip)

        self.tags_label.setVisible(has_tags)
        self.tags_label.setText("Tags: " + ", ".join(tag_names) if has_tags else "")
