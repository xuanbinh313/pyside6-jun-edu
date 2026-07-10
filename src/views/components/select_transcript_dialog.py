from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox
from src.models.exam import ExamSrtChunk
from src.viewmodels.select_transcript_viewmodel import SelectTranscriptViewModel
from ui_gen.ui_select_transcript_dialog import Ui_SelectTranscriptDialog


class SelectTranscriptDialog(QDialog):
    def __init__(
        self,
        exam_id: str,
        parent=None,
        viewmodel: SelectTranscriptViewModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Transcript Segment")
        self.resize(600, 400)
        self.exam_id = exam_id
        self.viewmodel = viewmodel or SelectTranscriptViewModel(exam_id)
        self.chunks: list[ExamSrtChunk] = []
        self.selected_chunks: list[ExamSrtChunk] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.ui = Ui_SelectTranscriptDialog()
        self.ui.setupUi(self)

        self.list_widget = self.ui.list_widget
        self.cancel_btn = self.ui.cancel_btn
        self.ok_btn = self.ui.ok_btn

        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._on_ok)

        self.chunks = self.viewmodel.list_chunks()
        for chunk in self.chunks:
            item = QListWidgetItem(
                f"[{chunk.start_time:.2f}s - {chunk.end_time:.2f}s]  {chunk.text}"
            )
            item.setData(Qt.ItemDataRole.UserRole, chunk)
            self.list_widget.addItem(item)

    def _on_ok(self) -> None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "No Selection", "Please select at least one transcript item."
            )
            return

        self.selected_chunks = sorted(
            [item.data(Qt.ItemDataRole.UserRole) for item in selected_items],
            key=lambda chunk: chunk.index,
        )
        self.accept()
