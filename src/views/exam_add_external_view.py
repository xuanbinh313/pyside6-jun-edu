from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget
from src.viewmodels.exam_add_external_viewmodel import ExamAddExternalViewModel
from ui_gen.ui_exam_add_external_view import Ui_ExamAddExternalView


class ExamAddExternalView(QWidget):
    def __init__(
        self,
        viewmodel: ExamAddExternalViewModel,
        go_back_callback: Callable[[], None],
        navigate_to_details_callback: Callable[[str], None],
    ):
        super().__init__()
        self.viewmodel = viewmodel
        self.go_back_callback = go_back_callback
        self.navigate_to_details = navigate_to_details_callback

        self.setup_ui()
        self.viewmodel.state_changed.connect(self.update_ui)
        self.viewmodel.progress_message.connect(self.show_progress)
        self.viewmodel.error_message.connect(self.show_error)
        self.viewmodel.exam_saved.connect(self.on_exam_saved)

    def setup_ui(self):
        self.ui = Ui_ExamAddExternalView()
        self.ui.setupUi(self)

        self.file_label = self.ui.file_label
        self.pick_btn = self.ui.pick_btn
        self.text_edit = self.ui.text_edit
        self.action_btn = self.ui.action_btn
        self.progress_label = self.ui.progress_label

        self.ui.back_btn.clicked.connect(self.go_back_callback)
        self.ui.reset_btn.clicked.connect(self.viewmodel.reset)
        self.pick_btn.clicked.connect(self.pick_file)
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.action_btn.clicked.connect(self.on_action_clicked)

    def pick_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav)"
        )
        if file_path:
            self.viewmodel.set_audio_file(file_path)

    def on_text_changed(self):
        self.viewmodel.set_text(self.text_edit.toPlainText())

    def on_action_clicked(self):
        if self.viewmodel.is_analyzed:
            self.viewmodel.add_or_update()
        else:
            self.viewmodel.analyze()

    def update_ui(self):
        if self.viewmodel.audio_file_name:
            self.file_label.setText(f"Selected: {self.viewmodel.audio_file_name}")
        else:
            self.file_label.setText("No audio selected")

        if self.text_edit.toPlainText() != self.viewmodel.text:
            self.text_edit.blockSignals(True)
            self.text_edit.setText(self.viewmodel.text)
            self.text_edit.blockSignals(False)

        self.pick_btn.setDisabled(
            self.viewmodel.is_loading or self.viewmodel.current_task_id is not None
        )
        self.action_btn.setDisabled(self.viewmodel.is_loading)

        if self.viewmodel.is_loading:
            self.action_btn.setText("Loading...")
        else:
            self.action_btn.setText(
                "Add or Update Exam" if self.viewmodel.is_analyzed else "Analyze"
            )
            self.progress_label.setText("")

    def show_progress(self, msg: str):
        self.progress_label.setText(msg)

    def show_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def on_exam_saved(self, exam_id: str):
        QMessageBox.information(self, "Success", "Exam created successfully!")
        self.navigate_to_details(exam_id)
