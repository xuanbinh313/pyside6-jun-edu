import os

from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QPushButton, QTextEdit, QWidget

from src.utils.helpers import get_local_media_path, local_media_filename_from_source
from src.viewmodels.exam_add_external_viewmodel import ExamAddExternalViewModel
from ui_gen.ui_exam_form_widget import Ui_ExamFormWidget


class ExamFormWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.external_viewmodel = ExamAddExternalViewModel(target_exam_id=self.viewmodel.exam_id)
        self._chunks_dirty = False
        self.setup_ui()
        self._connect_external_viewmodel()

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

        self.analyze_audio_btn = QPushButton("Analyze Audio")
        self.import_external_btn = QPushButton("Import Audio + Transcript")
        self.import_external_btn.setEnabled(False)
        self.ui.action_layout.addWidget(self.analyze_audio_btn)
        self.ui.action_layout.addWidget(self.import_external_btn)

        self.external_text_edit = QTextEdit(self)
        self.external_text_edit.setMinimumHeight(120)
        self.external_text_edit.setPlaceholderText("Extracted transcript text appears here. Edit before importing audio alignment.")
        self.ui.main_layout.insertWidget(2, self.external_text_edit)

        self.external_progress_label = QLabel("")
        self.external_progress_label.setWordWrap(True)
        self.external_progress_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        self.ui.main_layout.insertWidget(3, self.external_progress_label)

        self.upload_audio_btn.clicked.connect(self.on_upload_audio)
        self.attach_srt_btn.clicked.connect(self.on_attach_srt)
        self.import_csv_btn.clicked.connect(self.on_import_csv)
        self.analyze_audio_btn.clicked.connect(self.on_analyze_audio)
        self.import_external_btn.clicked.connect(self.on_import_external_audio)
        self.external_text_edit.textChanged.connect(self.on_external_text_changed)
        self.save_btn.clicked.connect(self.on_save)

    def _connect_external_viewmodel(self):
        self.external_viewmodel.state_changed.connect(self.update_external_import_ui)
        self.external_viewmodel.progress_message.connect(self.show_external_progress)
        self.external_viewmodel.error_message.connect(self.show_external_error)
        self.external_viewmodel.exam_saved.connect(self.on_external_exam_saved)

    def populate(self):
        if self.viewmodel.exam:
            self.title_input.setText(self.viewmodel.exam.title or "")
            self.description_input.setText(self.viewmodel.exam.description or "")
            audio_name = self.viewmodel.exam.audio_name or ""
            audio_path = str(get_local_media_path(audio_name)) if audio_name else ""
            self.audio_input.setText(audio_path)
            self.duration_input.setValue(self.viewmodel.exam.duration_minutes or 0)
            self.published_checkbox.setChecked(bool(self.viewmodel.exam.is_published))
        self.external_viewmodel.target_exam_id = self.viewmodel.exam_id

    def on_upload_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav)")
        if file_path:
            self.audio_input.setText(file_path)
            self.external_viewmodel.set_audio_file(file_path)

    def parse_srt(self, file_path):
        from src.repositories.sqlite.orm_models import ExamSrtChunk

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
        self._chunks_dirty = True
        QMessageBox.information(self, "Success", f"Parsed {len(chunks)} chunks from SRT.")

    def on_attach_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SRT", "", "SRT (*.srt)")
        if file_path:
            self.parse_srt(file_path)

    def on_import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV (*.csv)")
        if file_path:
            from src.repositories.sqlite.orm_models import ExamSrtChunk

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
            self._chunks_dirty = True
            QMessageBox.information(self, "Success", f"Parsed {len(chunks)} chunks from CSV.")

    def on_external_text_changed(self):
        self.external_viewmodel.set_text(self.external_text_edit.toPlainText())

    def on_analyze_audio(self):
        audio_path = self.audio_input.text().strip()
        if not audio_path or not os.path.exists(audio_path):
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav)")
            if not file_path:
                return
            audio_path = file_path
            self.audio_input.setText(audio_path)
        self.external_viewmodel.set_audio_file(audio_path)
        self.external_viewmodel.analyze()

    def on_import_external_audio(self):
        if not self.external_viewmodel.is_analyzed:
            QMessageBox.warning(self, "Analyze First", "Analyze an audio file before importing aligned transcript chunks.")
            return
        if not self._ensure_exam_saved():
            return
        self.external_viewmodel.target_exam_id = self.viewmodel.exam_id
        self.external_viewmodel.set_text(self.external_text_edit.toPlainText())
        self.external_viewmodel.add_or_update()

    def update_external_import_ui(self):
        text = self.external_viewmodel.text
        if self.external_text_edit.toPlainText() != text:
            self.external_text_edit.blockSignals(True)
            self.external_text_edit.setPlainText(text)
            self.external_text_edit.blockSignals(False)

        is_loading = self.external_viewmodel.is_loading
        self.upload_audio_btn.setDisabled(is_loading)
        self.attach_srt_btn.setDisabled(is_loading)
        self.import_csv_btn.setDisabled(is_loading)
        self.analyze_audio_btn.setDisabled(is_loading)
        self.import_external_btn.setDisabled(is_loading or not self.external_viewmodel.is_analyzed)

        if is_loading:
            self.analyze_audio_btn.setText("Loading...")
        else:
            self.analyze_audio_btn.setText("Analyze Audio")
            if not self.external_progress_label.text().startswith("Imported"):
                self.external_progress_label.setText("")

    def show_external_progress(self, msg):
        self.external_progress_label.setText(msg)

    def show_external_error(self, msg):
        QMessageBox.critical(self, "External Audio Import", msg)

    def on_external_exam_saved(self, exam_id):
        if self.external_viewmodel.imported_audio_path:
            self.audio_input.setText(self.external_viewmodel.imported_audio_path)
        count = self.external_viewmodel.imported_chunk_count
        self.external_progress_label.setText(f"Imported audio and {count} transcript chunks.")
        self.viewmodel.load_exam()
        QMessageBox.information(self, "Success", f"Imported audio and {count} transcript chunks.")

    def _ensure_exam_saved(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Title is required before importing audio.")
            return False
        self.viewmodel.save_exam(
            title,
            self.description_input.toPlainText(),
            self.duration_input.value(),
            self.published_checkbox.isChecked(),
            self.viewmodel.exam.audio_name if self.viewmodel.exam else None,
        )
        return bool(self.viewmodel.exam_id)

    def _audio_name_from_input(self):
        audio_source = self.audio_input.text().strip()
        if not audio_source:
            return None
        audio_name = local_media_filename_from_source(audio_source)
        self.audio_input.setText(str(get_local_media_path(audio_name)))
        return audio_name

    def on_save(self):
        try:
            audio_name = self._audio_name_from_input()
        except Exception as exc:
            QMessageBox.critical(
                self, "Audio Save Error", f"Could not save audio file:\n{exc}"
            )
            return
        self.viewmodel.save_exam(
            self.title_input.text(),
            self.description_input.toPlainText(),
            self.duration_input.value(),
            self.published_checkbox.isChecked(),
            audio_name,
        )
        if self._chunks_dirty:
            self.viewmodel.save_chunks()
            self._chunks_dirty = False
        QMessageBox.information(self, "Saved", "Exam details saved.")
