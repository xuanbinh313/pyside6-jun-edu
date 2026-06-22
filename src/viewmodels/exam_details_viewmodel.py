from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.models.exam import Exam, ExamContext, ExamQuestion, ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class ExamDetailsViewModel(QObject):
    data_loaded = Signal()
    data_saved = Signal()

    def __init__(self, exam_id=None, repo: IExamRepository | None = None):
        super().__init__()
        self.repo = repo or SQLiteExamRepository()
        self.exam_id = exam_id
        self.exam: Optional[Exam] = None
        self.srt_chunks: list[ExamSrtChunk] = []
        self.contexts: list[ExamContext] = []
        self.questions: list[ExamQuestion] = []

    def load_exam(self):
        if self.exam_id:
            self.exam, self.srt_chunks, self.contexts, self.questions = (
                self.repo.get_exam_details(self.exam_id)
            )
        else:
            self.exam = Exam(title="")
            self.srt_chunks = []
            self.contexts = []
            self.questions = []
        self.data_loaded.emit()

    def save_exam(
        self, title, description, duration_minutes, is_published, full_audio_url=None
    ):
        self.exam_id = self.repo.save_exam(
            exam_id=self.exam_id,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            is_published=is_published,
            full_audio_url=full_audio_url,
        )
        self.data_saved.emit()

    def save_chunks(self):
        if not self.exam_id:
            return

        self.repo.replace_srt_chunks(self.exam_id, self.srt_chunks)

    def duplicate_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        max_idx = max((c.index for c in self.srt_chunks), default=0)

        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=max_idx + 1,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text,
            hint=getattr(chunk, "hint", None),
        )
        self.srt_chunks.insert(list_idx + 1, new_chunk)
        return list_idx + 1, new_chunk

    def merge_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        if list_idx >= len(self.srt_chunks) - 1:
            return None, None

        next_chunk = self.srt_chunks[list_idx + 1]
        chunk.text = f"{chunk.text} {next_chunk.text}"
        chunk.end_time = next_chunk.end_time

        self.srt_chunks.pop(list_idx + 1)
        return list_idx, next_chunk
