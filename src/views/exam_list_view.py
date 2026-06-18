from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLabel

class ExamListView(QWidget):
    def __init__(self, viewmodel, navigate_to_details_callback):
        super().__init__()
        self.viewmodel = viewmodel
        self.navigate_to_details = navigate_to_details_callback
        
        self.setup_ui()
        self.viewmodel.data_changed.connect(self.on_data_changed)
        self.viewmodel.load_exams()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Exam List")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a73e8;")
        header_layout.addWidget(title)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search exams...")
        self.search_input.textChanged.connect(self.on_search)
        header_layout.addWidget(self.search_input)

        add_btn = QPushButton("Add Exam")
        add_btn.setStyleSheet("background-color: #1a73e8; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(lambda: self.navigate_to_details(None))
        header_layout.addWidget(add_btn)
        
        add_ext_btn = QPushButton("Add External")
        add_ext_btn.setStyleSheet("background-color: #34a853; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px;")
        add_ext_btn.clicked.connect(lambda: self.navigate_to_details("EXTERNAL"))
        header_layout.addWidget(add_ext_btn)
        
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Title", "Duration (mins)", "Published", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def on_search(self, text):
        self.viewmodel.set_search_query(text)

    def on_data_changed(self):
        self.table.setRowCount(0)
        for row, exam in enumerate(self.viewmodel.exams):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(exam.title))
            self.table.setItem(row, 1, QTableWidgetItem(str(exam.duration_minutes)))
            self.table.setItem(row, 2, QTableWidgetItem("Yes" if exam.is_published else "No"))
            
            # Action buttons
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
            
            self.table.setCellWidget(row, 3, actions_widget)
