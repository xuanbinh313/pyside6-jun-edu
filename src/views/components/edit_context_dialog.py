from PySide6.QtWidgets import QDialog, QMessageBox

import src.models.exam as exam_model
from src.models.database import get_session
from src.views.components.ui_edit_context_dialog import Ui_EditContextDialog


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
        self.ui = Ui_EditContextDialog()
        self.ui.setupUi(self)

        self.content_edit = self.ui.content_edit
        self.ui.header_label.setText(f"Editing Context [{self.context.context_type}]")
        self.ui.cancel_btn.clicked.connect(self.reject)
        self.ui.save_btn.clicked.connect(self._on_save)

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
