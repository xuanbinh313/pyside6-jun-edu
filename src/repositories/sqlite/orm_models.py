import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.util.typing import TypedDict

from src.repositories.sqlite.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    audio_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

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
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class AdditionalMeta(TypedDict):
    audio_start: float
    audio_end: float
    note: str


class QuestionAdditionalMeta(TypedDict):
    note: str

class ExamContent(TypedDict):
    text: str
    image_path: Optional[str]
    image_filename: Optional[str]

class AnswerSheet(TypedDict):
    listening_image_path: str
    reading_image_path: str
    prompt: str
class Part(TypedDict):
    part: int
    question_pdf_path: str
    question_pages: List[int]
    transcript_pdf_path: str
    transcript_pages: List[int]
    prompt: str
    context_text: str

class Payload(TypedDict):
    answer_sheet: AnswerSheet
    parts: List[Part]


class ExamContext(Base):
    __tablename__ = "exam_contexts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    part: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    context_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[ExamContent] = mapped_column(JSON, nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    additional_meta: Mapped[AdditionalMeta] = mapped_column(
        JSON,
        default=lambda: {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="contexts")
    questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion", back_populates="context", cascade="all, delete-orphan"
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


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
    additional_meta: Mapped[QuestionAdditionalMeta] = mapped_column(
        JSON,
        default=lambda: {"note": ""},
    )

    context: Mapped[Optional["ExamContext"]] = relationship(
        "ExamContext", back_populates="questions"
    )
    answers: Mapped[List["UserAnswer"]] = relationship(
        "UserAnswer", back_populates="question", cascade="all, delete-orphan"
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class UserQuestionTag(Base):
    __tablename__ = "user_question_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("exam_questions.id"), nullable=False
    )
    tag_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=str(datetime.now(timezone.utc)))
    dirty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
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
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    attempt: Mapped["ExamAttempt"] = relationship(
        "ExamAttempt", back_populates="answers"
    )
    question: Mapped["ExamQuestion"] = relationship(
        "ExamQuestion", back_populates="answers"
    )


class MediaFile(Base):
    __tablename__ = "mediafiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: str(datetime.now(timezone.utc)),
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: str(datetime.now(timezone.utc)),
    )
    dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ImportAgentTaskLocal(Base):
    __tablename__ = "import_agent_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    payload: Mapped[Payload] = mapped_column(JSON, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    auto_retry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    next_retry_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
