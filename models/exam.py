from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
import datetime
import uuid
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Exam(Base):
    __tablename__ = "exams"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    full_audio_url = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=False)
    user_id = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    srt_chunks = relationship("ExamSrtChunk", back_populates="exam", cascade="all, delete-orphan")

class ExamSrtChunk(Base):
    __tablename__ = "exam_srt_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(String, nullable=False)
    hint = Column(String, nullable=True)

    exam = relationship("Exam", back_populates="srt_chunks")
