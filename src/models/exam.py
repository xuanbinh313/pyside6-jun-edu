from pydantic import Field
import datetime
import json
import uuid
from typing import Optional

from pydantic import BaseModel, field_validator


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AdditionalMeta(BaseModel):
    audio_start: float = 0.0
    audio_end: float = 0.0
    note: str = ""
    image_filename: str = ""
    image_path: Optional[str] = None


class QuestionAdditionalMeta(BaseModel):
    note: str = ""


class ContextContent(BaseModel):
    text: str
    image_path: Optional[str] = None
    image_filename: Optional[str] = None


class ExamSrtChunk(BaseModel):
    index: int
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
    id: str = Field(default_factory=generate_uuid)
    exam_id: str = ""
    hint: Optional[str] = None
    user_id: Optional[str] = None


class ExamContext(BaseModel):
    exam_id: str
    context_type: str
    content: ContextContent
    id: str = Field(default_factory=generate_uuid)
    part: int = 1
    index: int = 0
    additional_meta: AdditionalMeta = Field(
        default_factory=lambda: AdditionalMeta(
            audio_start=0.0,
            audio_end=0.0,
            note="",
            image_filename="",
        )
    )
    user_id: Optional[str] = None
    questions: list["ExamQuestion"] = Field(default_factory=list)


class ExamQuestion(BaseModel):
    context_id: str
    question_number: int
    content: str
    correct_answer: str
    id: str = Field(default_factory=generate_uuid)
    question_type: str = "MULTIPLE_CHOICE"
    options: list[str] = Field(default_factory=list)
    additional_meta: QuestionAdditionalMeta = Field(
        default_factory=lambda: QuestionAdditionalMeta(note="")
    )
    user_id: Optional[str] = None
    context: Optional[ExamContext] = None

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return [value] if value else []
            if isinstance(decoded, list):
                return [str(option) for option in decoded]
            return [str(decoded)] if decoded is not None else []
        if isinstance(value, list):
            return [str(option) for option in value]
        return value


class UserQuestionTag(BaseModel):
    question_id: str
    tag_name: str
    id: str = Field(default_factory=generate_uuid)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: int = 1
    user_id: Optional[str] = None


class UserAnswer(BaseModel):
    attempt_id: str
    question_id: str
    is_correct: bool
    id: str = Field(default_factory=generate_uuid)
    user_choice: Optional[str] = None
    user_id: Optional[str] = None
    dirty: bool = False
    question: Optional[ExamQuestion] = None


class ExamAttempt(BaseModel):
    exam_id: str
    id: str = Field(default_factory=generate_uuid)
    total_correct: int = 0
    total_questions: int = 0
    final_score: Optional[float] = None
    duration_seconds: int = 0
    user_id: Optional[str] = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: bool = False
    answers: list[UserAnswer] = Field(default_factory=list)


class ImportAgentTask(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    status: str = "queued"
    payload: dict = Field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 3
    auto_retry: bool = True
    error_message: str = ""
    result: dict = Field(default_factory=dict)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    next_retry_at: Optional[datetime.datetime] = None


class Exam(BaseModel):
    title: str
    id: str = Field(default_factory=generate_uuid)
    description: Optional[str] = None
    audio_name: Optional[str] = None
    duration_minutes: int = 0
    is_published: bool = False
    user_id: Optional[str] = ""
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    srt_chunks: list[ExamSrtChunk] = Field(default_factory=list)
    contexts: list[ExamContext] = Field(default_factory=list)
    attempts: list[ExamAttempt] = Field(default_factory=list)
