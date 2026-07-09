import html
import json
from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QBoxLayout,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QWidget,
)
from shiboken6 import isValid
from src.models.exam import ExamQuestion
from src.views.components.exam_context_section import VocabularyTextBrowser
from ui_gen.ui_option_question_item import Ui_OptionQuestionItem

VocabularyCallback = Callable[[str, str], None]


class OptionVocabularyTextBrowser(VocabularyTextBrowser):
    """Vocabulary browser whose button can float above compact option rows."""

    def __init__(
        self,
        on_add_vocabulary: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(on_add_vocabulary, parent)
        self.add_vocabulary_button.setParent(
            None,
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint,
        )
        self.destroyed.connect(self.add_vocabulary_button.close)

    def _position_add_button(self) -> None:
        cursor = self.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", " ").strip()
        self._selected_text = " ".join(selected_text.split())
        if not self._selected_text:
            self.add_vocabulary_button.hide()
            return

        selection_start = QTextCursor(cursor)
        selection_start.setPosition(cursor.selectionStart())
        selection_rect = self.cursorRect(selection_start)
        button_size = self.add_vocabulary_button.sizeHint()
        selection_top = self.viewport().mapToGlobal(
            QPoint(selection_rect.center().x(), selection_rect.top())
        )
        self.add_vocabulary_button.move(
            selection_top.x() - (button_size.width() // 2),
            selection_top.y() - button_size.height() - 6,
        )
        self.add_vocabulary_button.show()
        self.add_vocabulary_button.raise_()


class OptionQuestionItem(QWidget):
    """Renders multiple-choice options for one ExamQuestion."""

    LETTER_MAP = ["A", "B", "C", "D"]

    def __init__(
        self,
        question: ExamQuestion,
        exam_id: Optional[str] = None,
        on_add_vocabulary: Optional[VocabularyCallback] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.question = question
        self.exam_id = exam_id
        self._on_add_vocabulary = on_add_vocabulary
        self.correct_answer = question.correct_answer
        try:
            self.orig_correct_idx = self.LETTER_MAP.index(self.correct_answer)
        except ValueError:
            self.orig_correct_idx = -1
        self.display_correct_letter = ""
        self._build(question)

    def _build(self, q: ExamQuestion) -> None:
        self.ui = Ui_OptionQuestionItem()
        self.ui.setupUi(self)

        self.stem_browser = self._replace_label(
            self.ui.stem,
            self.ui.header_layout,
            f"<b>Q{q.question_number}.</b> {html.escape(q.content)}",
            rich_text=True,
        )
        self.stem_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background: transparent;
                font-size: 13px;
                color: #202124;
            }
        """)
        self.ui.header_layout.setStretchFactor(self.stem_browser, 1)

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
                }
                QRadioButton:hover { color: #1a73e8; }
            """)
            radio.setProperty("orig_idx", orig_idx)
            self.btn_group.addButton(radio, display_pos)
            row_layout.addWidget(radio, 0, Qt.AlignmentFlag.AlignTop)

            option_label = OptionVocabularyTextBrowser(
                self._save_selected_vocabulary, row
            )
            option_label.setPlainText(f"{display_letter}.  {opt_text}")
            option_label.setStyleSheet("""
                QTextBrowser {
                    border: none;
                    background: transparent;
                    font-size: 12px;
                    color: #3c4043;
                }
            """)
            row_layout.addWidget(option_label, 1)
            self.ui.options_layout.addWidget(row)

        self._result_label = self._replace_label(
            self.ui.result_label,
            self.ui.main_layout,
            "",
            rich_text=True,
        )
        self._result_label.setVisible(False)
        self._result_label.setStyleSheet(
            """
            QTextBrowser {
                border: none;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
            }
            """
        )

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

    def _replace_label(
        self,
        label: QLabel,
        layout: QBoxLayout,
        text: str,
        *,
        rich_text: bool,
    ) -> OptionVocabularyTextBrowser:
        index = layout.indexOf(label)
        layout.removeWidget(label)
        label.setParent(None)
        label.deleteLater()

        browser = OptionVocabularyTextBrowser(
            self._save_selected_vocabulary, self
        )
        if rich_text:
            browser.setHtml(text)
        else:
            browser.setPlainText(text)
        layout.insertWidget(max(0, index), browser)
        return browser

    def _save_selected_vocabulary(self, word: str) -> None:
        if self._on_add_vocabulary is not None:
            self._on_add_vocabulary(word, self.question.context_id)

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

    def _on_check(self) -> None:
        self._result_label.setVisible(True)
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
