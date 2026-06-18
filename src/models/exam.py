from typing import List, Optional
import datetime
import uuid
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Base(DeclarativeBase):
    pass

class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    full_audio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    srt_chunks: Mapped[List["ExamSrtChunk"]] = relationship("ExamSrtChunk", back_populates="exam", cascade="all, delete-orphan")
    contexts: Mapped[List["ExamContext"]] = relationship("ExamContext", back_populates="exam", cascade="all, delete-orphan")
    questions: Mapped[List["ExamQuestion"]] = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")

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
    context_type: Mapped[str] = mapped_column(String, nullable=False) 
    content: Mapped[dict] = mapped_column(JSON, nullable=False) 
    index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="contexts")
    questions: Mapped[List["ExamQuestion"]] = relationship("ExamQuestion", back_populates="context")

class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), nullable=False)
    context_id: Mapped[Optional[str]] = mapped_column(ForeignKey("exam_contexts.id"), nullable=True)
    
    part: Mapped[int] = mapped_column(Integer, nullable=False) 
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False, default="MULTIPLE_CHOICE") 
    content: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=[]) 
    correct_answer: Mapped[str] = mapped_column(String, nullable=False)
    additional_meta: Mapped[dict] = mapped_column(JSON, default={}) 

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    context: Mapped[Optional["ExamContext"]] = relationship("ExamContext", back_populates="questions")

class UserQuestionTag(Base):
    __tablename__ = "user_question_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("exam_questions.id"), nullable=False)
    tag_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    dirty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)