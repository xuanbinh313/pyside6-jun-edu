from typing import Optional, cast
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QWidget
from src.utils.qt import clear_layout
from src.models.exam import ExamContext
from src.viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from ui_gen.ui_tag_menu_dialog import Ui_TagMenuDialog


class TagMenuDialog(QDialog):
    def __init__(self, target: ExamContext, parent: Optional[QWidget] = None, viewmodel: Optional[ExamDetailsViewModel] = None, context_id: Optional[str] = None):
        super().__init__(
            parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.target = target
        self.context_id = (
            context_id
            or getattr(target, "context_id", None)
            or getattr(target, "id", None)
        )
        self.viewmodel = viewmodel or self._find_viewmodel(parent)
        self.setFixedWidth(200)
        self._build_ui()

    def _find_viewmodel(self, widget: Optional[QWidget]) -> Optional[ExamDetailsViewModel]:
        while widget:
            viewmodel = getattr(widget, "viewmodel", None)
            if viewmodel is not None:
                return viewmodel
            widget = cast(Optional[QWidget], widget.parent())
        return None

    def _build_ui(self) -> None:
        self.ui = Ui_TagMenuDialog()
        self.ui.setupUi(self)

        self.tags_layout = self.ui.tags_layout
        self.new_tag_input = self.ui.new_tag_input
        self.new_tag_input.returnPressed.connect(self._on_add_tag)

        self._load_tags()

    def _load_tags(self):
        clear_layout(self.tags_layout)

        if self.viewmodel is None:
            return
        if not self.context_id:
            return

        all_tags = self.viewmodel.list_question_tags()
        current_tags = set(
            self.viewmodel.list_question_tags_for_context(self.context_id)
        )

        for tag_name in sorted(set(all_tags) | current_tags):
            cb = QCheckBox(tag_name)
            cb.setChecked(tag_name in current_tags)
            cb.setStyleSheet("""
                QCheckBox:checked {
                    color: #1a73e8;
                }
                QCheckBox::indicator:checked {
                    color: #1a73e8;
                }
            """)
            cb.stateChanged.connect(
                lambda state, t=tag_name: self._on_tag_state_changed(t, state)
            )
            self.tags_layout.addWidget(cb)

    def _on_tag_state_changed(self, tag_name: str, state: int) -> None:
        if self.viewmodel is None:
            return

        if not self.context_id:
            return

        self.viewmodel.set_context_tag(
            self.context_id,
            tag_name,
            state == Qt.CheckState.Checked.value,
        )

        self._notify_parent_tags_changed()

    def _on_add_tag(self):
        tag_name = self.new_tag_input.text().strip()
        if not tag_name:
            return
        if self.viewmodel is None:
            return
        if not self.context_id:
            return

        self.viewmodel.set_context_tag(self.context_id, tag_name, True)

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
