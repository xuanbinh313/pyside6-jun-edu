from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.exam import Exam, ExamContext, ExamQuestion, ExamSrtChunk


class IExamRepository(ABC):
    @abstractmethod
    def list_exams(self, search_query: str = "") -> list[Exam]:
        raise NotImplementedError

    @abstractmethod
    def delete_exam(self, exam_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_exam_details(
        self, exam_id: str
    ) -> tuple[Exam | None, list[ExamSrtChunk], list[ExamContext], list[ExamQuestion]]:
        raise NotImplementedError

    @abstractmethod
    def save_exam(
        self,
        *,
        exam_id: str | None,
        title: str,
        description: str | None,
        duration_minutes: int,
        is_published: bool,
        full_audio_url: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def replace_srt_chunks(self, exam_id: str, chunks: list[ExamSrtChunk]) -> None:
        raise NotImplementedError
