from PySide6.QtWidgets import QWidget
from src.views.components.exam_form_widget import ExamFormWidget
from src.views.components.exam_groups_widget import ExamGroupsWidget
from src.views.components.exam_transcript_widget import ExamTranscriptWidget
from ui_gen.ui_exam_details_view import Ui_ExamDetailsView


class ExamDetailsView(QWidget):
    def __init__(self, viewmodel, go_back_callback):
        super().__init__()
        self.viewmodel = viewmodel
        self.go_back_callback = go_back_callback

        self.setup_ui()
        self.viewmodel.data_loaded.connect(self.on_data_loaded)
        self.viewmodel.load_exam()

    def setup_ui(self):
        self.ui = Ui_ExamDetailsView()
        self.ui.setupUi(self)

        self.tabs = self.ui.tabs
        self.ui.back_btn.clicked.connect(self.go_back_callback)

        self.form_tab = ExamFormWidget(self.viewmodel)
        self.groups_tab = ExamGroupsWidget(self.viewmodel)
        self.transcript_tab = ExamTranscriptWidget(self.viewmodel)

        self.tabs.addTab(self.form_tab, "Exam Details")
        self.tabs.addTab(self.groups_tab, "Groups & Questions")
        self.tabs.addTab(self.transcript_tab, "Transcript")

    def on_data_loaded(self):
        self.form_tab.populate()
        self.groups_tab.populate()
        self.transcript_tab.populate()
