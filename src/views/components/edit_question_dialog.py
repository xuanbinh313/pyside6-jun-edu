import json

from PySide6.QtWidgets import QDialog, QMessageBox

import src.models.exam as exam_model
from src.models.database import get_session
from ui_gen.ui_edit_question_dialog import Ui_EditQuestionDialog


class EditQuestionDialog(QDialog):
    """Dialog that allows editing an ExamQuestion's core fields."""

    LETTERS = ["A", "B", "C", "D"]

    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question
        self.setWindowTitle(f"Edit Question {question.question_number}")
        self.resize(640, 520)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        self.ui = Ui_EditQuestionDialog()
        self.ui.setupUi(self)

        self.ui.header_label.setText(f"Editing Q{self.question.question_number}")
        self.part_combo = self.ui.part_combo
        self.answer_combo = self.ui.answer_combo
        self.content_edit = self.ui.content_edit
        self.option_edits = [
            self.ui.option_a_edit,
            self.ui.option_b_edit,
            self.ui.option_c_edit,
            self.ui.option_d_edit,
        ]

        self.part_combo.clear()
        for p in range(1, 8):
            self.part_combo.addItem(f"Part {p}", p)

        self.answer_combo.clear()
        for letter in self.LETTERS:
            self.answer_combo.addItem(letter)

        self.ui.cancel_btn.clicked.connect(self.reject)
        self.ui.save_btn.clicked.connect(self._on_save)

    def _populate(self):
        """Pre-fill form fields from the existing question."""
        q = self.question

        idx = self.part_combo.findData(q.part)
        if idx >= 0:
            self.part_combo.setCurrentIndex(idx)

        ans_idx = self.answer_combo.findText(q.correct_answer or "A")
        if ans_idx >= 0:
            self.answer_combo.setCurrentIndex(ans_idx)

        self.content_edit.setPlainText(q.content or "")

        try:
            opts = json.loads(q.options) if isinstance(q.options, str) else (q.options or [])
        except Exception:
            opts = []
        for i, edit in enumerate(self.option_edits):
            edit.setText(opts[i] if i < len(opts) else "")

    def _on_save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Validation", "Question content cannot be empty.")
            return

        options = [edit.text().strip() for edit in self.option_edits]
        if any(o == "" for o in options):
            QMessageBox.warning(self, "Validation", "All four options (A-D) must be filled in.")
            return

        session = get_session()
        try:
            db_q = session.query(exam_model.ExamQuestion).filter(
                exam_model.ExamQuestion.id == self.question.id
            ).first()
            if not db_q:
                QMessageBox.critical(self, "Error", "Question not found in database.")
                return

            db_q.part = self.part_combo.currentData()
            db_q.correct_answer = self.answer_combo.currentText()
            db_q.content = content
            db_q.options = options
            session.commit()

            self.question.part = db_q.part
            self.question.correct_answer = db_q.correct_answer
            self.question.content = db_q.content
            self.question.options = options

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error Saving", f"Could not save changes:\n{exc}")
            return
        finally:
            session.close()

        self.accept()
