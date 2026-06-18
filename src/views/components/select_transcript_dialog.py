
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QAbstractItemView
)
from PySide6.QtCore import Qt
from src.models.database import get_session
import src.models.exam as exam_model
# ─────────────────────────────────────────────────────────────────────────────
# SelectTranscriptDialog — dialog to select transcript chunks for a question
# ─────────────────────────────────────────────────────────────────────────────
class SelectTranscriptDialog(QDialog):
    def __init__(self, exam_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Transcript Segment")
        self.resize(600, 400)
        self.exam_id = exam_id
        self.selected_chunks = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        desc = QLabel("Select one or more transcript lines to set the audio segment:")
        desc.setStyleSheet("font-size: 13px; color: #5f6368;")
        layout.addWidget(desc)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # Load chunks from DB
        session = get_session()
        try:
            self.chunks = session.query(exam_model.ExamSrtChunk).filter(
                exam_model.ExamSrtChunk.exam_id == self.exam_id
            ).order_by(exam_model.ExamSrtChunk.index.asc()).all()
            for chunk in self.chunks:
                item = QListWidgetItem(f"[{chunk.start_time:.2f}s – {chunk.end_time:.2f}s]  {chunk.text}")
                item.setData(Qt.ItemDataRole.UserRole, chunk)
                self.list_widget.addItem(item)
        finally:
            session.close()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #dadce0;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton:hover { background-color: #f1f3f4; }
        """)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("Save Segment")
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one transcript item.")
            return
            
        self.selected_chunks = sorted(
            [item.data(Qt.ItemDataRole.UserRole) for item in selected_items],
            key=lambda c: c.index
        )
        self.accept()