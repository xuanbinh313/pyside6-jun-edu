import datetime
import json
import random
import time
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QObject, Signal
from src.repositories.sqlite.database import get_session
from src.repositories.sqlite.orm_models import (
    Exam,
    ExamAttempt,
    ExamContext,
    ExamQuestion,
    UserAnswer,
    UserQuestionTag,
)

LETTERS = ["A", "B", "C", "D"]


@dataclass
class AttemptSummary:
    id: str
    created_at: datetime.datetime
    duration_seconds: int
    total_correct: int
    total_questions: int
    final_score: Optional[float]

    @property
    def accuracy(self) -> float:
        if self.total_questions <= 0:
            return 0.0
        return self.total_correct / self.total_questions * 100.0


@dataclass
class ShuffledOption:
    display_index: int
    display_letter: str
    canonical_letter: str
    text: str


@dataclass
class QuestionSession:
    question_id: str
    question_number: int
    content: str
    correct_answer: str
    correct_text: str
    options: List[ShuffledOption]
    part: int
    context_id: str
    context_type: str
    context_text: str
    user_choice: Optional[str] = None
    skipped: bool = False

    @property
    def is_correct(self) -> bool:
        return self.user_choice == self.correct_answer


@dataclass
class AttemptAnswerDetail:
    question_id: str
    question_number: int
    part: int
    category: str
    content: str
    context_text: str
    correct_answer: str
    correct_text: str
    user_choice: Optional[str]
    user_text: str
    is_correct: bool

    @property
    def is_unanswered(self) -> bool:
        return self.user_choice is None


@dataclass
class CategoryBreakdown:
    name: str
    correct: int
    wrong: int
    skipped: int
    answers: List[AttemptAnswerDetail]

    @property
    def total(self) -> int:
        return self.correct + self.wrong + self.skipped

    @property
    def accuracy(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.correct / self.total * 100.0


@dataclass
class AttemptAnalytics:
    summary: AttemptSummary
    answers: List[AttemptAnswerDetail]
    overall_breakdown: List[CategoryBreakdown]
    part_breakdowns: dict[int, List[CategoryBreakdown]]

    @property
    def total_correct(self) -> int:
        return sum(1 for answer in self.answers if answer.is_correct)

    @property
    def total_unanswered(self) -> int:
        return sum(1 for answer in self.answers if answer.is_unanswered)

    @property
    def total_wrong(self) -> int:
        return sum(
            1
            for answer in self.answers
            if not answer.is_correct and not answer.is_unanswered
        )

    @property
    def accuracy_rate(self) -> float:
        if self.summary.total_questions <= 0:
            return 0.0
        return self.total_correct / self.summary.total_questions * 100.0


class ExamTakeViewModel(QObject):
    data_loaded = Signal()
    test_started = Signal()
    result_ready = Signal()
    error_message = Signal(str)

    def __init__(self, exam_id, user_id=None, parent=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.user_id = user_id
        self.exam = None
        self.contexts = []
        self.questions = []
        self.attempts = []
        self.parts = []
        self.tags = []
        self.mode = "practice"
        self.active_questions = []
        self.started_at = None
        self.completed_attempt_id = None
        self.total_correct = 0
        self.final_score = None

    def load_exam(self):
        session = get_session()
        try:
            self.exam = session.query(Exam).filter(Exam.id == self.exam_id).first()
            if not self.exam:
                self.error_message.emit("Exam not found.")
                return

            self.contexts = (
                session.query(ExamContext)
                .filter(ExamContext.exam_id == self.exam_id)
                .order_by(ExamContext.part.asc(), ExamContext.index.asc())
                .all()
            )
            self.questions = (
                session.query(ExamQuestion)
                .join(ExamContext, ExamQuestion.context_id == ExamContext.id)
                .filter(ExamContext.exam_id == self.exam_id)
                .order_by(ExamQuestion.question_number.asc())
                .all()
            )
            self.parts = sorted({ctx.part for ctx in self.contexts})
            self.tags = self._load_tags(session)
            self.attempts = self._load_attempts(session)

            session.expunge_all()
        finally:
            session.close()

        self.data_loaded.emit()

    def start_test(
        self,
        mode,
        selected_parts=None,
        selected_tags=None,
        question_ids=None,
    ):
        self.mode = mode
        selected_parts = set(selected_parts or [])
        selected_tags = set(selected_tags or [])
        question_ids = set(question_ids or [])
        question_tags = self._question_tags()
        context_map = {ctx.id: ctx for ctx in self.contexts}

        selected_questions = []
        for question in self.questions:
            ctx = context_map.get(question.context_id)
            if not ctx:
                continue
            if question_ids and question.id not in question_ids:
                continue
            if mode == "practice":
                if selected_parts and ctx.part not in selected_parts:
                    continue
                if selected_tags and not selected_tags.intersection(
                    question_tags.get(question.id, set())
                ):
                    continue
            selected_questions.append(question)

        if not selected_questions:
            self.error_message.emit("No questions match the selected mode or filters.")
            return

        self.active_questions = [
            self._build_question_session(question, context_map[question.context_id])
            for question in selected_questions
        ]
        self.started_at = time.monotonic()
        self.completed_attempt_id = None
        self.total_correct = 0
        self.final_score = None
        self.test_started.emit()

    def start_review_questions(self, question_ids):
        self.start_test("practice", question_ids=question_ids)

    def submit_answer(self, question_id, display_index):
        question = self._active_question(question_id)
        if not question:
            return
        for option in question.options:
            if option.display_index == display_index:
                question.user_choice = option.canonical_letter
                question.skipped = False
                return

    def skip_question(self, question_id):
        question = self._active_question(question_id)
        if question:
            question.user_choice = None
            question.skipped = True

    def complete_test(self):
        if not self.active_questions:
            self.error_message.emit("No active test to submit.")
            return

        duration_seconds = self.elapsed_seconds()
        self.total_correct = sum(1 for q in self.active_questions if q.is_correct)
        total_questions = len(self.active_questions)
        self.final_score = (
            self.total_correct / total_questions * 100.0 if total_questions else None
        )

        session = get_session()
        try:
            attempt = ExamAttempt(
                user_id=self.user_id,
                exam_id=self.exam_id,
                total_correct=self.total_correct,
                total_questions=total_questions,
                final_score=self.final_score,
                duration_seconds=duration_seconds,
                dirty=False,
            )
            session.add(attempt)
            session.flush()

            for question in self.active_questions:
                session.add(
                    UserAnswer(
                        attempt_id=attempt.id,
                        question_id=question.question_id,
                        user_choice=question.user_choice,
                        is_correct=question.is_correct,
                        dirty=False,
                    )
                )

            session.commit()
            self.completed_attempt_id = attempt.id
            self.attempts = self._load_attempts(session)
        except Exception as exc:
            session.rollback()
            self.error_message.emit(f"Could not save test result: {exc}")
            return
        finally:
            session.close()

        self.result_ready.emit()

    def elapsed_seconds(self):
        if self.started_at is None:
            return 0
        return max(0, int(time.monotonic() - self.started_at))

    def real_test_remaining_seconds(self):
        if self.mode != "real" or not self.exam:
            return None
        duration = max(0, int(self.exam.duration_minutes or 0) * 60)
        if duration <= 0:
            return None
        return max(0, duration - self.elapsed_seconds())

    def load_attempt_analytics(self, attempt_id):
        session = get_session()
        try:
            attempt = (
                session.query(ExamAttempt)
                .filter(
                    ExamAttempt.id == attempt_id,
                    ExamAttempt.exam_id == self.exam_id,
                    ExamAttempt.user_id == self.user_id,
                )
                .first()
            )
            if not attempt:
                self.error_message.emit("Attempt not found.")
                return None

            rows = (
                session.query(UserAnswer, ExamQuestion, ExamContext)
                .join(ExamQuestion, UserAnswer.question_id == ExamQuestion.id)
                .join(ExamContext, ExamQuestion.context_id == ExamContext.id)
                .filter(UserAnswer.attempt_id == attempt_id)
                .order_by(ExamContext.part.asc(), ExamQuestion.question_number.asc())
                .all()
            )

            answers = []
            for user_answer, question, context in rows:
                options = self._canonical_options(question.options)
                correct_answer = (question.correct_answer or "").strip().upper()
                correct_text = self._option_text(options, correct_answer)
                user_choice = (
                    user_answer.user_choice.strip().upper()
                    if user_answer.user_choice
                    else None
                )
                answers.append(
                    AttemptAnswerDetail(
                        question_id=question.id,
                        question_number=question.question_number,
                        part=context.part or 1,
                        category=question.question_type or "Question",
                        content=question.content,
                        context_text=self._context_text(context),
                        correct_answer=correct_answer,
                        correct_text=correct_text,
                        user_choice=user_choice,
                        user_text=self._option_text(options, user_choice),
                        is_correct=bool(user_answer.is_correct),
                    )
                )

            summary = AttemptSummary(
                id=attempt.id,
                created_at=attempt.created_at,
                duration_seconds=attempt.duration_seconds,
                total_correct=attempt.total_correct,
                total_questions=attempt.total_questions,
                final_score=attempt.final_score,
            )
            return AttemptAnalytics(
                summary=summary,
                answers=answers,
                overall_breakdown=self._breakdown_by_category(answers),
                part_breakdowns={
                    part: self._breakdown_by_category(
                        [answer for answer in answers if answer.part == part]
                    )
                    for part in sorted({answer.part for answer in answers})
                },
            )
        finally:
            session.close()

    def _build_question_session(self, question, context):
        raw_options = self._canonical_options(question.options)
        indexed_options = list(enumerate(raw_options))
        random.shuffle(indexed_options)

        shuffled = []
        for display_index, (canonical_index, option_text) in enumerate(indexed_options):
            shuffled.append(
                ShuffledOption(
                    display_index=display_index,
                    display_letter=LETTERS[display_index],
                    canonical_letter=LETTERS[canonical_index],
                    text=str(option_text),
                )
            )

        correct_answer = (question.correct_answer or "").strip().upper()
        correct_text = ""
        if correct_answer in LETTERS:
            correct_index = LETTERS.index(correct_answer)
            if correct_index < len(raw_options):
                correct_text = str(raw_options[correct_index])

        return QuestionSession(
            question_id=question.id,
            question_number=question.question_number,
            content=question.content,
            correct_answer=correct_answer,
            correct_text=correct_text,
            options=shuffled,
            part=context.part or 1,
            context_id=context.id,
            context_type=context.context_type,
            context_text=self._context_text(context),
        )

    def _canonical_options(self, options):
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                return []
        if not isinstance(options, list):
            return []
        return [str(option) for option in options[: len(LETTERS)]]

    def _option_text(self, options, letter):
        if letter not in LETTERS:
            return ""
        index = LETTERS.index(letter)
        if index >= len(options):
            return ""
        return options[index]

    def _breakdown_by_category(self, answers):
        grouped = {}
        for answer in answers:
            grouped.setdefault(answer.category, []).append(answer)

        breakdown = []
        for name in sorted(grouped):
            category_answers = grouped[name]
            correct = sum(1 for answer in category_answers if answer.is_correct)
            skipped = sum(1 for answer in category_answers if answer.is_unanswered)
            wrong = len(category_answers) - correct - skipped
            breakdown.append(
                CategoryBreakdown(
                    name=name,
                    correct=correct,
                    wrong=wrong,
                    skipped=skipped,
                    answers=category_answers,
                )
            )
        return breakdown

    def _active_question(self, question_id):
        for question in self.active_questions:
            if question.question_id == question_id:
                return question
        return None

    def _load_tags(self, session):
        rows = (
            session.query(UserQuestionTag.tag_name)
            .join(ExamQuestion, UserQuestionTag.question_id == ExamQuestion.id)
            .join(ExamContext, ExamQuestion.context_id == ExamContext.id)
            .filter(
                UserQuestionTag.user_id == self.user_id,
                ExamContext.exam_id == self.exam_id,
            )
            .distinct()
            .order_by(UserQuestionTag.tag_name.asc())
            .all()
        )
        return [row[0] for row in rows]

    def _load_attempts(self, session):
        rows = (
            session.query(ExamAttempt)
            .filter(
                ExamAttempt.user_id == self.user_id,
                ExamAttempt.exam_id == self.exam_id,
            )
            .order_by(ExamAttempt.created_at.desc())
            .all()
        )
        return [
            AttemptSummary(
                id=row.id,
                created_at=row.created_at,
                duration_seconds=row.duration_seconds,
                total_correct=row.total_correct,
                total_questions=row.total_questions,
                final_score=row.final_score,
            )
            for row in rows
        ]

    def _question_tags(self):
        session = get_session()
        try:
            rows = (
                session.query(UserQuestionTag.question_id, UserQuestionTag.tag_name)
                .join(ExamQuestion, UserQuestionTag.question_id == ExamQuestion.id)
                .join(ExamContext, ExamQuestion.context_id == ExamContext.id)
                .filter(
                    UserQuestionTag.user_id == self.user_id,
                    ExamContext.exam_id == self.exam_id,
                )
                .all()
            )
            result = {}
            for question_id, tag_name in rows:
                result.setdefault(question_id, set()).add(tag_name)
            return result
        finally:
            session.close()

    def _context_text(self, context):
        content = context.content
        if isinstance(content, dict):
            text = content.get("text", "")
            if text:
                return str(text)
            lines = content.get("srt_lines") or []
            if lines:
                return "\n".join(
                    str(line.get("text", ""))
                    for line in lines
                    if isinstance(line, dict)
                )
        return str(content or "")
