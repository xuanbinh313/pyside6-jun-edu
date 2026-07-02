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
        audio_name: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def replace_srt_chunks(self, exam_id: str, chunks: list[ExamSrtChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_question_tags(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def list_question_tags_for_context(self, context_id: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def set_context_tag(self, context_id: str, tag_name: str, enabled: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_contexts(
        self, exam_id: str, selected_tags: list[str] | None = None
    ) -> list[ExamContext]:
        raise NotImplementedError

    @abstractmethod
    def list_questions_for_context(self, context_id: str) -> list[ExamQuestion]:
        raise NotImplementedError

    @abstractmethod
    def get_context_question_numbers(self, context_id: str) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    def delete_contexts_and_questions(
        self, context_ids: list[str], question_ids: list[str]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ) -> ExamContext | None:
        raise NotImplementedError

    @abstractmethod
    def update_correct_answers(
        self, exam_id: str, answer_key: dict[int, str]
    ) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    def import_contexts_and_questions(
        self, exam_id: str, contexts_data: list[ExamContext], questions_data: list[ExamQuestion]
    ) -> dict:
        raise NotImplementedError
