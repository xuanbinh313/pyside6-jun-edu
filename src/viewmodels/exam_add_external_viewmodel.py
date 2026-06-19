import os
import time
import requests
import tempfile
import time as time_module
from PySide6.QtCore import QObject, Signal, QThread
from dotenv import load_dotenv
from src.models.database import get_session
from src.models.exam import Exam, ExamSrtChunk

load_dotenv()
TTS_AGENT_URL = os.getenv("TTS_AGENT_URL", "https://api.jun-edu.shop")

class Worker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(self.progress.emit, *self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class ExamAddExternalViewModel(QObject):
    state_changed = Signal()
    progress_message = Signal(str)
    error_message = Signal(str)
    exam_saved = Signal(str) # Emits the new exam_id

    def __init__(self, target_exam_id=None):
        super().__init__()
        self.target_exam_id = target_exam_id
        self.audio_file_path = None
        self.audio_file_name = None
        self.text = ""
        self.is_loading = False
        self.is_analyzed = False
        self.current_task_id = None
        self._worker = None
        self.imported_audio_path = ""
        self.imported_chunk_count = 0

    def set_audio_file(self, path):
        if path:
            self.audio_file_path = path
            self.audio_file_name = os.path.basename(path)
            self.is_analyzed = False
            self.current_task_id = None
            self.text = ""
            self.state_changed.emit()

    def set_text(self, text):
        self.text = text

    def poll_task_status(self, task_id, emit_progress):
        while True:
            time.sleep(2)
            emit_progress(f"Polling status for task {task_id}...")
            url = f"{TTS_AGENT_URL}/api/check-status/{task_id}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                if status == "completed":
                    return data.get("result")
                elif status == "failed":
                    raise Exception(f"Task failed: {data.get('error')}")
            else:
                raise Exception(f"Status check failed: {response.text}")

    def _analyze_task(self, emit_progress):
        url = f"{TTS_AGENT_URL}/api/extract-text"
        emit_progress("Uploading audio for extraction...")
        with open(self.audio_file_path, "rb") as f:
            files = {"audio": f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            if not task_id:
                raise Exception("No task_id returned from server")
            
            self.current_task_id = task_id
            return self.poll_task_status(task_id, emit_progress)
        else:
            raise Exception(f"Error starting analysis: {response.text}")

    def analyze(self):
        if not self.audio_file_path:
            self.error_message.emit("Please select an audio file first.")
            return

        self.is_loading = True
        self.state_changed.emit()

        self._worker = Worker(self._analyze_task)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.finished.connect(self._on_analyze_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analyze_finished(self, result):
        self.text = result.get("text", "")
        self.is_analyzed = True
        self.is_loading = False
        self.state_changed.emit()

    def _on_error(self, err_msg):
        self.is_loading = False
        self.error_message.emit(err_msg)
        self.state_changed.emit()

    def _add_update_task(self, emit_progress):
        url = f"{TTS_AGENT_URL}/api/align-audio"
        emit_progress("Sending text for alignment...")
        data = {
            "task_id": self.current_task_id,
            "text": self.text
        }
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            resp_data = response.json()
            task_id = resp_data.get("task_id")
            result = self.poll_task_status(task_id, emit_progress)
            
            content = result.get("content", [])
            url_audio = result.get("url_audio", "")
            
            # Download audio
            full_audio_url = url_audio if url_audio.startswith("http") else f"{TTS_AGENT_URL}{url_audio}"
            emit_progress("Downloading aligned audio...")
            audio_resp = requests.get(full_audio_url)
            if audio_resp.status_code == 200:
                name_file = os.path.splitext(self.audio_file_name)[0] if self.audio_file_name else "audio"
                file_name = f"{name_file}.wav"
                temp_dir = tempfile.gettempdir()
                media_dir = os.path.join(temp_dir, "jun_edu_media")
                os.makedirs(media_dir, exist_ok=True)
                
                timestamp = int(time_module.time() * 1000)
                unique_file_name = f"{timestamp}_{file_name}"
                target_path = os.path.join(media_dir, unique_file_name)
                
                with open(target_path, "wb") as f:
                    f.write(audio_resp.content)
                    
                # Save to DB
                emit_progress("Saving exam to database...")
                session = get_session()
                try:
                    if self.target_exam_id:
                        exam = session.query(Exam).filter(Exam.id == self.target_exam_id).first()
                        if not exam:
                            raise Exception("Target exam not found.")
                        exam.full_audio_url = target_path
                        session.query(ExamSrtChunk).filter(
                            ExamSrtChunk.exam_id == exam.id
                        ).delete(synchronize_session="fetch")
                    else:
                        exam = Exam(
                            title=self.audio_file_name or "External Exam",
                            description="Generated from external service",
                            duration_minutes=120,
                            full_audio_url=target_path,  # Storing absolute path for playback
                            is_published=False,
                            user_id="local_user"
                        )
                        session.add(exam)
                        session.flush()

                    for idx, item in enumerate(content):
                        chunk = ExamSrtChunk(
                            exam_id=exam.id,
                            index=idx,
                            start_time=float(item.get("start", 0.0)),
                            end_time=float(item.get("end", 0.0)),
                            text=str(item.get("text", ""))
                        )
                        session.add(chunk)
                    session.commit()
                    exam_id = exam.id
                    return {
                        "exam_id": exam_id,
                        "full_audio_url": target_path,
                        "chunk_count": len(content),
                    }
                finally:
                    session.close()
            else:
                raise Exception("Failed to download audio.")
        else:
            raise Exception(f"Error aligning audio: {response.text}")

    def add_or_update(self):
        if not self.audio_file_path or not self.text:
            self.error_message.emit("Audio and text are required.")
            return

        self.is_loading = True
        self.state_changed.emit()

        self._worker = Worker(self._add_update_task)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.finished.connect(self._on_add_update_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_add_update_finished(self, result):
        self.is_loading = False
        self.imported_audio_path = result.get("full_audio_url", "")
        self.imported_chunk_count = int(result.get("chunk_count", 0) or 0)
        self.state_changed.emit()
        self.exam_saved.emit(result["exam_id"])

    def reset(self):
        self.audio_file_path = None
        self.audio_file_name = None
        self.text = ""
        self.is_loading = False
        self.is_analyzed = False
        self.current_task_id = None
        self.imported_audio_path = ""
        self.imported_chunk_count = 0
        self.state_changed.emit()
