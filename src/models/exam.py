import datetime
import json
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AdditionalMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    audio_start: float = 0.0
    audio_end: float = 0.0
    note: str = ""
    image_filename: str = ""
    image_path: Optional[str] = None


class QuestionAdditionalMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    note: str = ""


class ContextContent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    text: str
    image_path: Optional[str] = None
    image_filename: Optional[str] = None

class SrtWord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    word: str
    start: float
    end: float


class AdditionalSrtChunkMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    words: List[SrtWord] = Field(default_factory=list)

    @field_validator("words", mode="before")
    @classmethod
    def normalize_words(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return []

class ExamSrtChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    index: int
    start_time: float = 0.0
    end_time: float = 0.0
    text: str = ""
    id: str = Field(default_factory=generate_uuid)
    exam_id: str = ""
    hint: Optional[str] = None
    user_id: Optional[str] = None
    additional_meta: AdditionalSrtChunkMeta = Field(
        default_factory=lambda: AdditionalSrtChunkMeta(words=[])
    )

    @field_validator("additional_meta", mode="before")
    @classmethod
    def normalize_additional_meta(cls, value: Any) -> Any:
        if value is None:
            return {"words": []}
        if isinstance(value, dict) and value.get("words") is None:
            return {**value, "words": []}
        return value

class ExamQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return [value] if value else []
            if isinstance(decoded, list):
                decoded_list: list[object] = decoded
                return [str(option) for option in decoded_list]
            return [str(decoded)] if decoded is not None else []
        if isinstance(value, list):
            value_list: list[object] = value
            return [str(option) for option in value_list]
        return [str(value)] if value is not None else []

class ExamContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    questions: list[ExamQuestion] = []


class UserQuestionTag(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    context_id: str
    tag_name: str
    id: str = Field(default_factory=generate_uuid)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    dirty: int = 1
    user_id: Optional[str] = None


class Vocabulary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    word: str
    meaning: Optional[str] = None
    status: int = 1
    source_text: Optional[str] = None
    ord: int = 0
    due_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    stability: float = 0.0
    difficulty: float = 0.0
    reps: int = 0
    lapses: int = 0
    step: Optional[int] = None
    data: dict[str, Any] = Field(default_factory=dict)
    state: int = 0
    last_review_at: Optional[datetime.datetime] = None
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    id: str = Field(default_factory=generate_uuid)
    context_id: Optional[str] = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    user_id: Optional[str] = None


class UserAnswer(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attempt_id: str
    question_id: str
    is_correct: bool
    id: str = Field(default_factory=generate_uuid)
    user_choice: Optional[str] = None
    user_id: Optional[str] = None
    dirty: bool = False
    question: Optional[ExamQuestion] = None


class ExamAttempt(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    answers: list[UserAnswer] = []


class ImportAgentTask(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    status: str = "queued"
    payload: dict = Field(default_factory=dict)
    ocr: str = ""
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
    model_config = ConfigDict(from_attributes=True)
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


# --- TẦNG CÂU HỎI (QUESTION) ---
class QuestionMetaSchema(BaseModel):
    note: str = Field(
        default="", 
        description="Dịch nghĩa câu hỏi, các lựa chọn và giải thích chi tiết ngữ pháp bằng tiếng Việt."
    )

class QuestionSchema(BaseModel):
    question_number: int = Field(description="Số thứ tự câu hỏi (ví dụ: 101, 102).")
    question_type: str = Field(default="MULTIPLE_CHOICE", description="Loại câu hỏi.")
    content: str = Field(description="Nội dung câu hỏi tiếng Anh chứa phần điền khuyết '-------'.")
    options: list[str] = Field(description="Danh sách các phương án lựa chọn (thường có 4 đáp án).")
    correct_answer: str = Field(description="Đáp án đúng (A, B, C hoặc D).")
    additional_meta: QuestionMetaSchema = Field(default_factory=QuestionMetaSchema)


# --- TẦNG NGỮ CẢNH (CONTEXT) ---
class ContextContentSchema(BaseModel):
    text: str = Field(default="", description="Văn bản đoạn văn nếu có. Với Part 5 để chuỗi rỗng ''.")

class ContextMetaSchema(BaseModel):
    audio_start: float = Field(default=0.0, description="Thời gian bắt đầu audio (mặc định 0.0 với Reading).")
    audio_end: float = Field(default=0.0, description="Thời gian kết thúc audio (mặc định 0.0 với Reading).")
    note: str = Field(default="", description="Ghi chú ngữ cảnh phụ nếu có.")

class ContextSchema(BaseModel):
    id: str = Field(description="Mã định danh context tự sinh theo format 'ctx_101'.")
    part: int = Field(default=5, description="Số Part của bài thi TOEIC (ví dụ: 5).")
    context_type: str = Field(default="STANDALONE", description="Loại ngữ cảnh (ví dụ: STANDALONE cho Part 5).")
    content: ContextContentSchema = Field(default_factory=ContextContentSchema)
    index: int = Field(description="Chỉ mục sắp xếp tăng dần từ 0.")
    additional_meta: ContextMetaSchema = Field(default_factory=ContextMetaSchema)
    questions: List[QuestionSchema] = Field(description="Danh sách câu hỏi thuộc ngữ cảnh này.")


# --- TẦNG ĐẦU RA TỔNG (RESPONSE) ---
class ToeicPartResponseSchema(BaseModel):
    contexts: List[ContextSchema] = Field(description="Mảng chứa toàn bộ các ngữ cảnh và câu hỏi của đề thi.")


class SrtChunkMapping(BaseModel):
    """One exam context mapped to a detected SRT chunk window."""

    context_id: str
    start_chunk_index: int
    end_chunk_index: int


class SrtMappingResponseSchema(BaseModel):
    """Structured output returned by the SRT mapping agent."""

    mappings: List[SrtChunkMapping]

class MediaFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    updated_at: str 
    is_deleted: bool
    user_id: Optional[str]
    created_at: str
