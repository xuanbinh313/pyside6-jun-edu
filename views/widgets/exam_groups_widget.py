from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ExamGroupsWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        label = QLabel("Groups & Questions (Empty - No Integration Needed)")
        label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(label)
