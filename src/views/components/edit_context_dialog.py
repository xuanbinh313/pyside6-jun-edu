
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QTextEdit
)
from src.models.database import get_session
import src.models.exam as exam_model
# ─────────────────────────────────────────────────────────────────────────────
# EditContextDialog — inline editor for an ExamContext (READING_PASSAGE)
# ─────────────────────────────────────────────────────────────────────────────
class EditContextDialog(QDialog):
    """Simple editor for an ExamContext's text content."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Edit Context")
        self.resize(640, 420)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-size: 12px; color: #3c4043; }
            QTextEdit {
                border: 1px solid #dadce0; border-radius: 6px;
                padding: 6px 8px; font-size: 12px; background-color: white;
            }
            QTextEdit:focus { border-color: #1a73e8; }
            QPushButton#save_btn {
                background-color: #1a73e8; color: white; font-weight: bold;
                border-radius: 6px; padding: 8px 20px; font-size: 12px;
            }
            QPushButton#save_btn:hover { background-color: #1558b0; }
            QPushButton#cancel_btn {
                background-color: white; color: #3c4043;
                border: 1px solid #dadce0; border-radius: 6px;
                padding: 8px 20px; font-size: 12px;
            }
            QPushButton#cancel_btn:hover { background-color: #f1f3f4; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        header = QLabel(f"✏️  Editing Context  [{self.context.context_type}]")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        root.addWidget(header)

        desc = QLabel("Content (text field for READING_PASSAGE; raw JSON for other types):")
        root.addWidget(desc)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Context content…")
        root.addWidget(self.content_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("💾  Save")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _populate(self):
        content = self.context.content
        if isinstance(content, dict):
            self.content_edit.setPlainText(content.get("text", ""))
        else:
            self.content_edit.setPlainText(str(content or ""))

    def _on_save(self):
        raw = self.content_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Validation", "Content cannot be empty.")
            return
        session = get_session()
        try:
            db_ctx = session.query(exam_model.ExamContext).filter(
                exam_model.ExamContext.id == self.context.id
            ).first()
            if not db_ctx:
                QMessageBox.critical(self, "Error", "Context not found in database.")
                return
            if isinstance(db_ctx.content, dict):
                new_content = dict(db_ctx.content)
                new_content["text"] = raw
            else:
                new_content = {"text": raw}
            db_ctx.content = new_content
            session.commit()
            self.context.content = new_content
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error Saving", f"Could not save:\n{exc}")
            return
        finally:
            session.close()
        self.accept()