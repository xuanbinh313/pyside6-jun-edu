from __future__ import annotations

from src.models.exam import ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class ExamTranscriptViewModel:
    def __init__(self, exam=None, repo: IExamRepository | None = None):
        self.repo = repo or SQLiteExamRepository()
        self.exam = exam
        self.srt_chunks = []

    def load_chunks(self, chunks):
        self.srt_chunks = chunks

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

    def save_chunks(self):
        if not self.exam or not self.exam.id:
            return

        self.repo.replace_srt_chunks(self.exam.id, self.srt_chunks)

    @property
    def exam_id(self):
        return self.exam.id if self.exam else None

    def list_contexts(self, selected_tags: list[str] | None = None):
        if not self.exam_id:
            return []
        return self.repo.list_contexts(self.exam_id, selected_tags)

    def context_question_numbers(self, context_id: str) -> list[int]:
        return self.repo.get_context_question_numbers(context_id)

    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ):
        return self.repo.update_context_audio_segment(
            context_id, audio_start, audio_end
        )
