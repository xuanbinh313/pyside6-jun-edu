from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from src.views.components.ui_exam_form_widget import Ui_ExamFormWidget


class ExamFormWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_ExamFormWidget()
        self.ui.setupUi(self)

        self.title_input = self.ui.title_input
        self.description_input = self.ui.description_input
        self.audio_input = self.ui.audio_input
        self.duration_input = self.ui.duration_input
        self.published_checkbox = self.ui.published_checkbox
        self.upload_audio_btn = self.ui.upload_audio_btn
        self.attach_srt_btn = self.ui.attach_srt_btn
        self.import_csv_btn = self.ui.import_csv_btn
        self.save_btn = self.ui.save_btn

        self.upload_audio_btn.clicked.connect(self.on_upload_audio)
        self.attach_srt_btn.clicked.connect(self.on_attach_srt)
        self.import_csv_btn.clicked.connect(self.on_import_csv)
        self.save_btn.clicked.connect(self.on_save)

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
            for line in lines[1:]:
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
        if self.viewmodel.exam:
            self.viewmodel.exam.full_audio_url = self.audio_input.text()

        self.viewmodel.save_exam(
            self.title_input.text(),
            self.description_input.toPlainText(),
            self.duration_input.value(),
            self.published_checkbox.isChecked()
        )
