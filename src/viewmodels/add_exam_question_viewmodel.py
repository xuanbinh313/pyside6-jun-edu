from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject
from src.models.exam import ExamContext, ExamQuestion
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository
from src.utils.helpers import get_local_media_path, optimize_image_to_webp_file


@dataclass
class QuestionFormValue:
    id: str | None
    question_number: int
    question_type: str
    content: str
    note: str
    options: list[str]
    correct_answer: str


@dataclass
class ContextFormValue:
    context_id: str | None
    part: int
    context_type: str
    content: dict[str, Any]
    index: int
    audio_start: float
    audio_end: float
    note: str
    questions: list[QuestionFormValue]
    removed_question_ids: set[str]


@dataclass
class SaveContextResult:
    context: ExamContext
    questions: list[ExamQuestion]


class AddExamQuestionViewModel(QObject):
    def __init__(
        self,
        exam_id: str | None,
        context: ExamContext | None = None,
        repo: IExamRepository | None = None,
    ) -> None:
        super().__init__()
        self.exam_id = exam_id
        self.context = context
        self.saved_context_id = getattr(context, "id", None)
        self.repo: IExamRepository = repo or SQLiteExamRepository()

    def default_numbers(self) -> tuple[int, int]:
        return self.repo.get_add_question_defaults(self.exam_id)

    def list_questions_for_context(self, context_id: str) -> list[ExamQuestion]:
        return self.repo.list_questions_for_context(context_id)

    def save_diagram_image_file(
        self, image_path: str, current_filename: str
    ) -> str:
        current_path = Path(image_path)
        if current_filename and current_path == get_local_media_path(current_filename):
            return current_filename

        return optimize_image_to_webp_file(image_path, current_filename)

    def save(self, form: ContextFormValue) -> SaveContextResult:
        self._validate(form)
        question_payloads: list[dict[str, Any]] = [
            {
                "id": question.id,
                "question_number": question.question_number,
                "question_type": question.question_type,
                "content": question.content,
                "note": question.note,
                "options": question.options,
                "correct_answer": question.correct_answer,
            }
            for question in form.questions
        ]
        context, questions = self.repo.save_context_questions(
            exam_id=self.exam_id,
            context_id=form.context_id,
            part=form.part,
            context_type=form.context_type,
            content=form.content,
            index=form.index,
            additional_meta={
                "audio_start": form.audio_start,
                "audio_end": form.audio_end,
                "note": form.note,
            },
            questions=question_payloads,
            removed_question_ids=form.removed_question_ids,
        )
        self.context = context
        self.saved_context_id = context.id
        return SaveContextResult(context=context, questions=questions)

    def _validate(self, form: ContextFormValue) -> None:
        for question in form.questions:
            if not question.content:
                raise ValueError("Question content cannot be empty.")
            if question.question_type == "MULTIPLE_CHOICE" and any(
                not option for option in question.options
            ):
                raise ValueError("All four options are required for multiple choice.")

        question_numbers = [question.question_number for question in form.questions]
        if len(question_numbers) != len(set(question_numbers)):
            raise ValueError("Question numbers must be unique in this context.")
