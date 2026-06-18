import json

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout, QTextEdit, QGroupBox
)
from src.models.database import get_session
import src.models.exam as exam_model
# ─────────────────────────────────────────────────────────────────────────────
# EditQuestionDialog — inline editor for a single ExamQuestion
# ─────────────────────────────────────────────────────────────────────────────
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

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
                color: #3c4043;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #1a73e8;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #1a73e8;
                border: 1px solid #dadce0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton#save_btn {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton#save_btn:hover { background-color: #1558b0; }
            QPushButton#cancel_btn {
                background-color: white;
                color: #3c4043;
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton#cancel_btn:hover { background-color: #f1f3f4; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        header = QLabel(f"✏️  Editing  Q{self.question.question_number}")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        root.addWidget(header)

        # ── Meta row (Part + Correct Answer) ──────────────────────────────────
        meta_group = QGroupBox("Meta")
        meta_form = QFormLayout(meta_group)
        meta_form.setSpacing(8)

        self.part_combo = QComboBox()
        for p in range(1, 8):
            self.part_combo.addItem(f"Part {p}", p)
        meta_form.addRow("Part:", self.part_combo)

        self.answer_combo = QComboBox()
        for letter in self.LETTERS:
            self.answer_combo.addItem(letter)
        meta_form.addRow("Correct Answer:", self.answer_combo)
        root.addWidget(meta_group)

        # ── Content ───────────────────────────────────────────────────────────
        content_group = QGroupBox("Question Content")
        cg_layout = QVBoxLayout(content_group)
        self.content_edit = QTextEdit()
        self.content_edit.setFixedHeight(80)
        self.content_edit.setPlaceholderText("Enter question text here…")
        cg_layout.addWidget(self.content_edit)
        root.addWidget(content_group)

        # ── Options A–D ───────────────────────────────────────────────────────
        opts_group = QGroupBox("Options (A / B / C / D)")
        opts_form = QFormLayout(opts_group)
        opts_form.setSpacing(8)

        self.option_edits = []
        for letter in self.LETTERS:
            edit = QLineEdit()
            edit.setPlaceholderText(f"Option {letter}…")
            opts_form.addRow(f"{letter}:", edit)
            self.option_edits.append(edit)
        root.addWidget(opts_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("💾  Save Changes")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _populate(self):
        """Pre-fill form fields from the existing question."""
        q = self.question

        # Part
        idx = self.part_combo.findData(q.part)
        if idx >= 0:
            self.part_combo.setCurrentIndex(idx)

        # Correct answer
        ans_idx = self.answer_combo.findText(q.correct_answer or "A")
        if ans_idx >= 0:
            self.answer_combo.setCurrentIndex(ans_idx)

        # Content
        self.content_edit.setPlainText(q.content or "")

        # Options
        try:
            opts = json.loads(q.options) if isinstance(q.options, str) else (q.options or [])
        except Exception:
            opts = []
        for i, edit in enumerate(self.option_edits):
            edit.setText(opts[i] if i < len(opts) else "")

    # ── Save ──────────────────────────────────────────────────────────────────
    def _on_save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Validation", "Question content cannot be empty.")
            return

        options = [edit.text().strip() for edit in self.option_edits]
        if any(o == "" for o in options):
            QMessageBox.warning(self, "Validation", "All four options (A–D) must be filled in.")
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

            # Reflect changes back onto the in-memory object so the caller
            # can refresh the list item without a full reload.
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