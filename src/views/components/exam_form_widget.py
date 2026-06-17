from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QSpinBox, QCheckBox, QPushButton, QHBoxLayout, QFileDialog, QMessageBox

class ExamFormWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        form_layout.addRow("Title:", self.title_input)
        
        self.description_input = QTextEdit()
        form_layout.addRow("Description:", self.description_input)
        
        self.audio_layout = QHBoxLayout()
        self.audio_input = QLineEdit()
        self.audio_layout.addWidget(self.audio_input)
        
        self.upload_audio_btn = QPushButton("Upload Audio")
        self.upload_audio_btn.clicked.connect(self.on_upload_audio)
        self.audio_layout.addWidget(self.upload_audio_btn)
        
        form_layout.addRow("Audio URL:", self.audio_layout)
        
        self.duration_input = QSpinBox()
        self.duration_input.setRange(0, 1000)
        form_layout.addRow("Duration (minutes):", self.duration_input)
        
        self.published_checkbox = QCheckBox()
        form_layout.addRow("Published:", self.published_checkbox)
        
        layout.addLayout(form_layout)
        
        # SRT / CSV buttons
        action_layout = QHBoxLayout()
        self.attach_srt_btn = QPushButton("Attach SRT")
        self.attach_srt_btn.clicked.connect(self.on_attach_srt)
        action_layout.addWidget(self.attach_srt_btn)
        
        self.import_csv_btn = QPushButton("Import CSV")
        self.import_csv_btn.clicked.connect(self.on_import_csv)
        action_layout.addWidget(self.import_csv_btn)
        layout.addLayout(action_layout)
        
        self.save_btn = QPushButton("Save Details")
        self.save_btn.setStyleSheet("background-color: #34a853; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
        self.save_btn.clicked.connect(self.on_save)
        layout.addWidget(self.save_btn)
        
    def populate(self):
        if self.viewmodel.exam:
            self.title_input.setText(self.viewmodel.exam.title or "")
            self.description_input.setText(self.viewmodel.exam.description or "")
            self.audio_input.setText(self.viewmodel.exam.full_audio_url or "")
            self.duration_input.setValue(self.viewmodel.exam.duration_minutes or 0)
            self.published_checkbox.setChecked(bool(self.viewmodel.exam.is_published))
            
    def on_upload_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav)")
        if file_path:
            self.audio_input.setText(file_path)

    def parse_srt(self, file_path):
        from src.models.exam import ExamSrtChunk
        chunks = []
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Basic SRT parser (for demonstration/migration)
        current_chunk = None
        idx = 0
        for line in lines:
            line = line.strip()
            if not line:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = None
                continue
            if line.isdigit() and current_chunk is None:
                current_chunk = ExamSrtChunk(index=idx)
                idx += 1
            elif "-->" in line and current_chunk:
                # 00:00:01,000 --> 00:00:03,000
                times = line.split("-->")
                def parse_time(t_str):
                    parts = t_str.strip().replace(",", ".").split(":")
                    if len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    return 0.0
                current_chunk.start_time = parse_time(times[0])
                current_chunk.end_time = parse_time(times[1])
            elif current_chunk:
                if current_chunk.text:
                    current_chunk.text += " " + line
                else:
                    current_chunk.text = line
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        self.viewmodel.srt_chunks = chunks
        QMessageBox.information(self, "Success", f"Parsed {len(chunks)} chunks from SRT.")

    def on_attach_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SRT", "", "SRT (*.srt)")
        if file_path:
            self.parse_srt(file_path)
            
    def on_import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV (*.csv)")
        if file_path:
            from src.models.exam import ExamSrtChunk
            chunks = []
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Assuming CSV: index, start, end, text
            for i, line in enumerate(lines[1:]): # skip header
                parts = line.strip().split(",")
                if len(parts) >= 4:
                    chunk = ExamSrtChunk(
                        index=int(parts[0]),
                        start_time=float(parts[1]),
                        end_time=float(parts[2]),
                        text=",".join(parts[3:])
                    )
                    chunks.append(chunk)
            self.viewmodel.srt_chunks = chunks
            QMessageBox.information(self, "Success", f"Parsed {len(chunks)} chunks from CSV.")

    def on_save(self):
        # We need to update audio_url in viewmodel first so we don't lose it
        if self.viewmodel.exam:
            self.viewmodel.exam.full_audio_url = self.audio_input.text()
            
        self.viewmodel.save_exam(
            self.title_input.text(),
            self.description_input.toPlainText(),
            self.duration_input.value(),
            self.published_checkbox.isChecked()
        )
