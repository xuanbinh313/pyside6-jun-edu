from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.models.exam import (
    ContextSchema,
    Exam,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    QuestionSchema,
    Vocabulary,
)


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
    def add_vocabulary(
        self, word: str, context_id: str | None = None
    ) -> Vocabulary:
        raise NotImplementedError

    @abstractmethod
    def list_vocabulary(self) -> list[Vocabulary]:
        raise NotImplementedError

    @abstractmethod
    def update_vocabulary_status(self, vocab_id: str, status: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_vocabulary_meaning(self, vocab_id: str, meaning: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_vocabulary(self, vocab_id: str) -> None:
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
    def get_add_question_defaults(self, exam_id: str | None) -> tuple[int, int]:
        raise NotImplementedError

    @abstractmethod
    def save_context_questions(
        self,
        *,
        exam_id: str | None,
        context_id: str | None,
        part: int,
        context_type: str,
        content: dict[str, Any],
        index: int,
        additional_meta: dict[str, Any],
        questions: list[dict[str, Any]],
        removed_question_ids: set[str],
    ) -> tuple[ExamContext, list[ExamQuestion]]:
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
        self, exam_id: str, contexts_data: list[ContextSchema], questions_data: list[QuestionSchema]
    ) -> dict:
        raise NotImplementedError
