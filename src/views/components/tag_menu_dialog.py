
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel,
    QDialog, QCheckBox, QLineEdit
)
from PySide6.QtCore import Qt
from src.models.database import get_session
import src.models.exam as exam_model
# ─────────────────────────────────────────────────────────────────────────────
# TagMenuDialog — floating menu to manage question tags
# ─────────────────────────────────────────────────────────────────────────────
class TagMenuDialog(QDialog):
    def __init__(self, question, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.question = question
        self.user_id = "local_user"
        self.setStyleSheet("""
            QDialog {
                border: 1px solid #dadce0;
                background-color: white;
                border-radius: 6px;
            }
        """)
        self.setFixedWidth(200)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Manage Tags")
        title.setStyleSheet("font-weight: bold; color: #1a73e8; font-size: 12px;")
        layout.addWidget(title)

        # List of tags checkable
        self.tags_layout = QVBoxLayout()
        self.tags_layout.setSpacing(4)
        layout.addLayout(self.tags_layout)

        # Add input field
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Add new tag...")
        self.new_tag_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
        """)
        self.new_tag_input.returnPressed.connect(self._on_add_tag)
        layout.addWidget(self.new_tag_input)

        # Load existing tags and question's tags
        self._load_tags()

    def _load_tags(self):
        # Clear tags layout
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                del item

        session = get_session()
        try:
            # All unique tags for this user
            all_tags_rows = session.query(exam_model.UserQuestionTag.tag_name).filter(
                exam_model.UserQuestionTag.user_id == self.user_id
            ).distinct().all()
            all_tags = [r[0] for r in all_tags_rows]

            # Tags currently applied to this question
            current_tags_rows = session.query(exam_model.UserQuestionTag.tag_name).filter(
                exam_model.UserQuestionTag.user_id == self.user_id,
                exam_model.UserQuestionTag.question_id == self.question.id
            ).all()
            current_tags = set(r[0] for r in current_tags_rows)

            for tag_name in all_tags:
                cb = QCheckBox(tag_name)
                cb.setChecked(tag_name in current_tags)
                cb.setStyleSheet("font-size: 11px; color: #3c4043;")
                cb.stateChanged.connect(lambda state, t=tag_name: self._on_tag_state_changed(t, state))
                self.tags_layout.addWidget(cb)
        finally:
            session.close()

    def _on_tag_state_changed(self, tag_name, state):
        session = get_session()
        try:
            if state == Qt.CheckState.Checked.value:
                # Add tag
                exists = session.query(exam_model.UserQuestionTag).filter(
                    exam_model.UserQuestionTag.user_id == self.user_id,
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name
                ).first()
                if not exists:
                    new_tag = exam_model.UserQuestionTag(
                        user_id=self.user_id,
                        question_id=self.question.id,
                        tag_name=tag_name,
                        dirty=1
                    )
                    session.add(new_tag)
                    session.commit()
            else:
                # Delete tag
                session.query(exam_model.UserQuestionTag).filter(
                    exam_model.UserQuestionTag.user_id == self.user_id,
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name
                ).delete()
                session.commit()
        finally:
            session.close()

        # Notify parent widget to refresh filter if necessary
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_tag_changed"):
                parent_widget.on_question_tag_changed()
                break
            parent_widget = parent_widget.parent()

    def _on_add_tag(self):
        tag_name = self.new_tag_input.text().strip()
        if not tag_name:
            return
        
        session = get_session()
        try:
            exists = session.query(exam_model.UserQuestionTag).filter(
                exam_model.UserQuestionTag.user_id == self.user_id,
                exam_model.UserQuestionTag.question_id == self.question.id,
                exam_model.UserQuestionTag.tag_name == tag_name
            ).first()
            if not exists:
                new_tag = exam_model.UserQuestionTag(
                    user_id=self.user_id,
                    question_id=self.question.id,
                    tag_name=tag_name,
                    dirty=1
                )
                session.add(new_tag)
                session.commit()
        finally:
            session.close()

        self.new_tag_input.clear()
        self._load_tags()

        # Notify parent widget to refresh filter if necessary
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_tag_changed"):
                parent_widget.on_question_tag_changed()
                break
            parent_widget = parent_widget.parent()