import datetime
import uuid
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.util.typing import TypedDict

from src.models.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    full_audio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    srt_chunks: Mapped[List["ExamSrtChunk"]] = relationship(
        "ExamSrtChunk", back_populates="exam", cascade="all, delete-orphan"
    )
    contexts: Mapped[List["ExamContext"]] = relationship(
        "ExamContext", back_populates="exam", cascade="all, delete-orphan"
    )
    attempts: Mapped[List["ExamAttempt"]] = relationship(
        "ExamAttempt", back_populates="exam", cascade="all, delete-orphan"
    )


class ExamSrtChunk(Base):
    __tablename__ = "exam_srt_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="srt_chunks")


class ExamContext(Base):
    __tablename__ = "exam_contexts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    part: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    context_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="contexts")
    questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion", back_populates="context"
    )


class AdditionalMeta(TypedDict):
    audio_start: float
    audio_end: float
    note: str


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    context_id: Mapped[str] = mapped_column(
        ForeignKey("exam_contexts.id"), nullable=False
    )

    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String, nullable=False, default="MULTIPLE_CHOICE"
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=[])
    correct_answer: Mapped[str] = mapped_column(String, nullable=False)
    additional_meta: Mapped[AdditionalMeta] = mapped_column(
        JSON,
        default=lambda: {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
    )

    context: Mapped[Optional["ExamContext"]] = relationship(
        "ExamContext", back_populates="questions"
    )
    answers: Mapped[List["UserAnswer"]] = relationship(
        "UserAnswer", back_populates="question"
    )


class UserQuestionTag(Base):
    __tablename__ = "user_question_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("exam_questions.id"), nullable=False
    )
    tag_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="attempts")
    answers: Mapped[List["UserAnswer"]] = relationship(
        "UserAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("exam_questions.id"), nullable=False
    )
    user_choice: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped["ExamQuestion"] = relationship("ExamQuestion", back_populates="answers")
