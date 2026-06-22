import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional, TypedDict


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AdditionalMeta(TypedDict):
    audio_start: float
    audio_end: float
    note: str


class QuestionAdditionalMeta(TypedDict):
    note: str


@dataclass
class ExamSrtChunk:
    index: int
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
    id: str = field(default_factory=generate_uuid)
    exam_id: str = ""
    hint: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class ExamContext:
    exam_id: str
    context_type: str
    content: dict
    id: str = field(default_factory=generate_uuid)
    part: int = 1
    index: int = 0
    additional_meta: AdditionalMeta = field(
        default_factory=lambda: {"audio_start": 0.0, "audio_end": 0.0, "note": ""}
    )
    user_id: Optional[str] = None
    questions: list["ExamQuestion"] = field(default_factory=list)


@dataclass
class ExamQuestion:
    context_id: str
    question_number: int
    content: str
    correct_answer: str
    id: str = field(default_factory=generate_uuid)
    question_type: str = "MULTIPLE_CHOICE"
    options: list[str] = field(default_factory=list)
    additional_meta: QuestionAdditionalMeta = field(default_factory=lambda: {"note": ""})
    user_id: Optional[str] = None
    context: Optional[ExamContext] = None


@dataclass
class UserQuestionTag:
    question_id: str
    tag_name: str
    id: str = field(default_factory=generate_uuid)
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: int = 1
    user_id: Optional[str] = None


@dataclass
class UserAnswer:
    attempt_id: str
    question_id: str
    is_correct: bool
    id: str = field(default_factory=generate_uuid)
    user_choice: Optional[str] = None
    user_id: Optional[str] = None
    dirty: bool = False
    question: Optional[ExamQuestion] = None


@dataclass
class ExamAttempt:
    exam_id: str
    id: str = field(default_factory=generate_uuid)
    total_correct: int = 0
    total_questions: int = 0
    final_score: Optional[float] = None
    duration_seconds: int = 0
    user_id: Optional[str] = None
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: bool = False
    answers: list[UserAnswer] = field(default_factory=list)


@dataclass
class Exam:
    title: str
    id: str = field(default_factory=generate_uuid)
    description: Optional[str] = None
    full_audio_url: Optional[str] = None
    duration_minutes: int = 0
    is_published: bool = False
    user_id: Optional[str] = ""
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    srt_chunks: list[ExamSrtChunk] = field(default_factory=list)
    contexts: list[ExamContext] = field(default_factory=list)
    attempts: list[ExamAttempt] = field(default_factory=list)
