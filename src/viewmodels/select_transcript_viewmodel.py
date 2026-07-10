from __future__ import annotations

from src.models.exam import ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class SelectTranscriptViewModel:
    def __init__(
        self, exam_id: str, repo: IExamRepository | None = None
    ) -> None:
        self.exam_id = exam_id
        self.repo: IExamRepository = repo or SQLiteExamRepository()

    def list_chunks(self) -> list[ExamSrtChunk]:
        return self.repo.list_srt_chunks(self.exam_id)
