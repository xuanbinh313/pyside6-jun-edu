from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)
from ui_gen.ui_exam_list_view import Ui_ExamListView


class ExamListView(QWidget):
    def __init__(self, viewmodel, navigate_to_details_callback, navigate_to_take_callback):
        super().__init__()
        self.viewmodel = viewmodel
        self.navigate_to_details = navigate_to_details_callback
        self.navigate_to_take = navigate_to_take_callback

        self.setup_ui()
        self.viewmodel.data_changed.connect(self.on_data_changed)
        self.viewmodel.load_exams()

    def setup_ui(self):
        self.ui = Ui_ExamListView()
        self.ui.setupUi(self)

        self.search_input = self.ui.search_input
        self.table = self.ui.table

        self.search_input.textChanged.connect(self.on_search)
        self.ui.add_btn.clicked.connect(lambda: self.navigate_to_details(None))
        self.ui.add_ext_btn.clicked.connect(lambda: self.navigate_to_details("EXTERNAL"))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def on_search(self, text):
        self.viewmodel.set_search_query(text)

    def on_data_changed(self):
        self.table.setRowCount(0)
        for row, exam in enumerate(self.viewmodel.exams):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(exam.title))
            self.table.setItem(row, 1, QTableWidgetItem(str(exam.duration_minutes)))
            self.table.setItem(row, 2, QTableWidgetItem("Yes" if exam.is_published else "No"))

            start_btn = QPushButton("Start")
            start_btn.setStyleSheet("background-color: #1a73e8; color: white; font-weight: bold;")
            start_btn.clicked.connect(lambda checked, e_id=exam.id: self.navigate_to_take(e_id))
            self.table.setCellWidget(row, 3, start_btn)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, e_id=exam.id: self.navigate_to_details(e_id))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("color: red;")
            delete_btn.clicked.connect(lambda checked, e_id=exam.id: self.viewmodel.delete_exam(e_id))
            actions_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 4, actions_widget)
