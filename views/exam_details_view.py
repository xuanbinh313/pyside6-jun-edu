from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget
from views.widgets.exam_form_widget import ExamFormWidget
from views.widgets.exam_groups_widget import ExamGroupsWidget
from views.widgets.exam_transcript_widget import ExamTranscriptWidget

class ExamDetailsView(QWidget):
    def __init__(self, viewmodel, go_back_callback):
        super().__init__()
        self.viewmodel = viewmodel
        self.go_back_callback = go_back_callback
        
        self.setup_ui()
        self.viewmodel.data_loaded.connect(self.on_data_loaded)
        self.viewmodel.load_exam()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header (AppBar equivalent)
        header_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.go_back_callback)
        header_layout.addWidget(back_btn)
        
        title = QLabel("Exam Management")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a73e8;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        
        self.form_tab = ExamFormWidget(self.viewmodel)
        self.groups_tab = ExamGroupsWidget(self.viewmodel)
        self.transcript_tab = ExamTranscriptWidget(self.viewmodel)
        
        self.tabs.addTab(self.form_tab, "Exam Details")
        self.tabs.addTab(self.groups_tab, "Groups & Questions")
        self.tabs.addTab(self.transcript_tab, "Transcript")
        
        self.tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 20px; font-weight: bold; }
            QTabBar::tab:selected { background-color: #1a73e8; color: white; border-radius: 4px; }
        """)
        
        layout.addWidget(self.tabs)
        
    def on_data_loaded(self):
        self.form_tab.populate()
        self.transcript_tab.populate()
