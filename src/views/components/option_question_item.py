import html
import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QWidget,
)
from shiboken6 import isValid
from src.models.exam import ExamQuestion
from ui_gen.ui_option_question_item import Ui_OptionQuestionItem


class OptionQuestionItem(QWidget):
    """Renders multiple-choice options for one ExamQuestion."""

    LETTER_MAP = ["A", "B", "C", "D"]

    def __init__(self, question: ExamQuestion, exam_id: Optional[str] = None, parent: Optional[QWidget] = None):
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

    def _build(self, q: ExamQuestion):
        self.ui = Ui_OptionQuestionItem()
        self.ui.setupUi(self)

        self.ui.stem.setText(f"<b>Q{q.question_number}.</b> {q.content}")
        self.ui.stem.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.ui.stem.setStyleSheet("font-size: 13px; color: #202124; padding: 4px 0;")
        self.ui.header_layout.setStretchFactor(self.ui.stem, 1)

        self.ui.edit_q_btn.setVisible(False)

        self.ui.header_layout.removeWidget(self.ui.tag_btn)
        self.ui.tag_btn.setParent(None)
        self.ui.tag_btn.deleteLater()

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

            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            radio = QRadioButton()
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
            row_layout.addWidget(radio, 0, Qt.AlignmentFlag.AlignTop)

            option_label = QLabel(f"{display_letter}.  {opt_text}", row)
            option_label.setTextFormat(Qt.TextFormat.PlainText)
            option_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            option_label.setWordWrap(True)
            option_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #3c4043;
                    padding: 3px 6px;
                }
            """)
            row_layout.addWidget(option_label, 1)
            self.ui.options_layout.addWidget(row)

        self._result_label = self.ui.result_label
        self._result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
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
            f"{safe_note}</span>"
        )

    def _answer_note(self) -> str:
        return self.question.additional_meta.note

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
        return isValid(self) and hasattr(self, "ui")
