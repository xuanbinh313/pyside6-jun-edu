from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox
from PySide6.QtCore import Qt

class ExamAddExternalView(QWidget):
    def __init__(self, viewmodel, go_back_callback, navigate_to_details_callback):
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
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.go_back_callback)
        header_layout.addWidget(back_btn)
        
        title = QLabel("Add External Exam")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a73e8;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.viewmodel.reset)
        header_layout.addWidget(reset_btn)
        
        layout.addLayout(header_layout)
        
        # File selector
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No audio selected")
        file_layout.addWidget(self.file_label, stretch=1)
        
        self.pick_btn = QPushButton("Select MP3")
        self.pick_btn.clicked.connect(self.pick_file)
        file_layout.addWidget(self.pick_btn)
        layout.addLayout(file_layout)
        
        # Text Box
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Extracted text will appear here...")
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)
        
        # Action button
        self.action_btn = QPushButton("Analyze")
        self.action_btn.setStyleSheet("background-color: #1a73e8; color: white; padding: 15px; font-size: 16px; font-weight: bold;")
        self.action_btn.clicked.connect(self.on_action_clicked)
        layout.addWidget(self.action_btn)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #666; font-style: italic;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

    def pick_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav)")
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
        # Update labels
        if self.viewmodel.audio_file_name:
            self.file_label.setText(f"Selected: {self.viewmodel.audio_file_name}")
        else:
            self.file_label.setText("No audio selected")
            
        # Update text if different
        if self.text_edit.toPlainText() != self.viewmodel.text:
            self.text_edit.blockSignals(True)
            self.text_edit.setText(self.viewmodel.text)
            self.text_edit.blockSignals(False)
            
        # Update button state
        self.pick_btn.setDisabled(self.viewmodel.is_loading or self.viewmodel.current_task_id is not None)
        self.action_btn.setDisabled(self.viewmodel.is_loading)
        
        if self.viewmodel.is_loading:
            self.action_btn.setText("Loading...")
        else:
            self.action_btn.setText("Add or Update Exam" if self.viewmodel.is_analyzed else "Analyze")
            self.progress_label.setText("")

    def show_progress(self, msg):
        self.progress_label.setText(msg)
        
    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        
    def on_exam_saved(self, exam_id):
        QMessageBox.information(self, "Success", "Exam created successfully!")
        self.navigate_to_details(exam_id)
