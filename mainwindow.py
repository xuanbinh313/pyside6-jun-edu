import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Add current directory to path if needed, but normally running from jun-edu is fine.
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from views.exam_list_view import ExamListView
from views.exam_details_view import ExamDetailsView
from views.exam_add_external_view import ExamAddExternalView
from viewmodels.exam_list_viewmodel import ExamListViewModel
from viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from viewmodels.exam_add_external_viewmodel import ExamAddExternalViewModel
from models.database import init_db

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jun Edu - Exam Management")
        self.resize(1000, 700)
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.list_viewmodel = ExamListViewModel()
        self.list_view = ExamListView(self.list_viewmodel, self.navigate_to_details)
        
        self.stacked_widget.addWidget(self.list_view)
        
    def navigate_to_details(self, exam_id):
        if exam_id == "EXTERNAL":
            self.ext_viewmodel = ExamAddExternalViewModel()
            self.ext_view = ExamAddExternalView(self.ext_viewmodel, self.navigate_to_list, self.navigate_to_details)
            self.stacked_widget.addWidget(self.ext_view)
            self.stacked_widget.setCurrentWidget(self.ext_view)
        else:
            self.details_viewmodel = ExamDetailsViewModel(exam_id)
            self.details_view = ExamDetailsView(self.details_viewmodel, self.navigate_to_list)
            self.stacked_widget.addWidget(self.details_view)
            self.stacked_widget.setCurrentWidget(self.details_view)
        
    def navigate_to_list(self):
        # Refresh list and switch back
        self.list_viewmodel.load_exams()
        self.stacked_widget.setCurrentWidget(self.list_view)
        
        # Optionally remove the details view
        widget = self.stacked_widget.widget(1)
        if widget:
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
