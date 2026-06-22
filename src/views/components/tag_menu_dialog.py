from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog

from src.repositories.sqlite import orm_models as exam_model
from src.repositories.sqlite.database import get_session
from src.utils.qt import clear_layout
from ui_gen.ui_tag_menu_dialog import Ui_TagMenuDialog


class TagMenuDialog(QDialog):
    def __init__(self, question, parent=None):
        super().__init__(
            parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.question = question
        self.setFixedWidth(200)
        self._build_ui()

    def _build_ui(self):
        self.ui = Ui_TagMenuDialog()
        self.ui.setupUi(self)

        self.tags_layout = self.ui.tags_layout
        self.new_tag_input = self.ui.new_tag_input
        self.new_tag_input.returnPressed.connect(self._on_add_tag)

        self._load_tags()

    def _load_tags(self):
        clear_layout(self.tags_layout)

        session = get_session()
        try:
            all_tags_rows = (
                session.query(exam_model.UserQuestionTag.tag_name).distinct().all()
            )
            all_tags = [r[0] for r in all_tags_rows]

            current_tags_rows = (
                session.query(exam_model.UserQuestionTag.tag_name)
                .filter(
                    exam_model.UserQuestionTag.question_id == self.question.id,
                )
                .all()
            )
            current_tags = set(r[0] for r in current_tags_rows)

            for tag_name in all_tags:
                cb = QCheckBox(tag_name)
                cb.setChecked(tag_name in current_tags)
                cb.setStyleSheet("font-size: 11px; color: #3c4043;")
                cb.stateChanged.connect(
                    lambda state, t=tag_name: self._on_tag_state_changed(t, state)
                )
                self.tags_layout.addWidget(cb)
        finally:
            session.close()

    def _on_tag_state_changed(self, tag_name, state):
        session = get_session()
        try:
            if state == Qt.CheckState.Checked.value:
                exists = (
                    session.query(exam_model.UserQuestionTag)
                    .filter(
                        exam_model.UserQuestionTag.question_id == self.question.id,
                        exam_model.UserQuestionTag.tag_name == tag_name,
                    )
                    .first()
                )
                if not exists:
                    new_tag = exam_model.UserQuestionTag(
                        user_id=self.user_id,
                        question_id=self.question.id,
                        tag_name=tag_name,
                        dirty=1,
                    )
                    session.add(new_tag)
                    session.commit()
            else:
                session.query(exam_model.UserQuestionTag).filter(
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name,
                ).delete()
                session.commit()
        finally:
            session.close()

        self._notify_parent_tags_changed()

    def _on_add_tag(self):
        tag_name = self.new_tag_input.text().strip()
        if not tag_name:
            return

        session = get_session()
        try:
            exists = (
                session.query(exam_model.UserQuestionTag)
                .filter(
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name,
                )
                .first()
            )
            if not exists:
                new_tag = exam_model.UserQuestionTag(
                    user_id=self.user_id,
                    question_id=self.question.id,
                    tag_name=tag_name,
                    dirty=1,
                )
                session.add(new_tag)
                session.commit()
        finally:
            session.close()

        self.new_tag_input.clear()
        self._load_tags()
        self._notify_parent_tags_changed()

    def _notify_parent_tags_changed(self):
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_tag_changed"):
                parent_widget.on_question_tag_changed()
                break
            parent_widget = parent_widget.parent()
