import os
import time
import time as time_module
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv
from PySide6.QtCore import QObject, QThread, Signal
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository
from src.utils.helpers import get_local_media_path, unique_media_filename

load_dotenv()
TTS_AGENT_URL = os.getenv("TTS_AGENT_URL", "https://api.jun-edu.xyz")


def _extract_segments(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw_segments = result.get("segments")
    if raw_segments is None:
        raw_segments = result.get("content")
    if not isinstance(raw_segments, list):
        return []
    return [segment for segment in raw_segments if isinstance(segment, dict)]


class Worker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        func: Callable[[Callable[[str], None], Any], Any],
        *args: Any,
        **kwargs: Any,
    ):
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
    exam_saved = Signal(str)  # Emits the new exam_id

    def __init__(
        self,
        target_exam_id: Optional[str] = None,
        repo: Optional[IExamRepository] = None,
    ):
        super().__init__()
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.target_exam_id = target_exam_id
        self.audio_file_path: Optional[str] = None
        self.audio_file_name: Optional[str] = None
        self.text: str = ""
        self.is_loading: bool = False
        self.is_analyzed: bool = False
        self.current_task_id: Optional[str] = None
        self._worker: Optional[Worker] = None
        self.imported_audio_path: str = ""
        self.imported_chunk_count = 0

    def set_audio_file(self, path: str):
        if path:
            self.audio_file_path = path
            self.audio_file_name = os.path.basename(path)
            self.is_analyzed = False
            self.current_task_id = None
            self.text = ""
            self.state_changed.emit()

    def set_text(self, text: str):
        self.text = text

    def poll_task_status(self, task_id: str, emit_progress: Callable[[str], None]):
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

    def _analyze_task(self, emit_progress: Callable[[str], None]):
        url = f"{TTS_AGENT_URL}/api/extract-text"
        emit_progress("Uploading audio for extraction...")
        if not self.audio_file_path:
            raise Exception("Audio file path is not set.")
        if not os.path.exists(self.audio_file_path):
            raise Exception("Audio file does not exist.")
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

    def _on_error(self, err_msg: str):
        self.is_loading = False
        self.error_message.emit(err_msg)
        self.state_changed.emit()

    def _add_update_task(self, emit_progress: Callable[[str], None]):
        url = f"{TTS_AGENT_URL}/api/align-audio"
        emit_progress("Sending text for alignment...")
        data = {"task_id": self.current_task_id, "text": self.text}
        response = requests.post(url, data=data)

        if response.status_code == 200:
            resp_data = response.json()
            task_id = resp_data.get("task_id")
            result = self.poll_task_status(task_id, emit_progress)

            content = _extract_segments(result)
            url_audio = result.get("url_audio", "")

            # Download audio
            audio_url = (
                url_audio
                if url_audio.startswith("http")
                else f"{TTS_AGENT_URL}{url_audio}"
            )
            emit_progress("Downloading aligned audio...")
            audio_resp = requests.get(audio_url)
            if audio_resp.status_code == 200:
                timestamp = int(time_module.time() * 1000)
                audio_name = unique_media_filename(
                    f"{timestamp}_{self.audio_file_name}"
                )
                target_path = get_local_media_path(audio_name)

                with open(target_path, "wb") as f:
                    f.write(audio_resp.content)

                emit_progress("Saving exam to database...")
                exam_id = self.repo.save_external_aligned_exam(
                    target_exam_id=self.target_exam_id,
                    title=self.audio_file_name or "External Exam",
                    description="Generated from external service",
                    duration_minutes=120,
                    audio_name=audio_name,
                    segments=content,
                )
                return {
                    "exam_id": exam_id,
                    "audio_name": audio_name,
                    "audio_path": str(target_path),
                    "chunk_count": len(content),
                }
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
        self.imported_audio_path = result.get("audio_path", "")
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
