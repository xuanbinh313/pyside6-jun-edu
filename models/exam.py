from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON
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
    full_audio_url = Column(String, nullable=True) # File nghe tổng của cả đề (nếu có)
    duration_minutes = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=False)
    user_id = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Mối quan hệ tuyến tính siêu sạch
    srt_chunks = relationship("ExamSrtChunk", back_populates="exam", cascade="all, delete-orphan")
    contexts = relationship("ExamContext", back_populates="exam", cascade="all, delete-orphan")
    questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")

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
    
class ExamContext(Base):
    """ BẢNG TỐI CAO: ÔM TRỌN TẤT CẢ CÁC LOẠI ĐỀ BÀI / BỐI CẢNH """
    __tablename__ = "exam_contexts"

    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    
    # Định danh loại bối cảnh: 'AUDIO_SRT', 'READING_PASSAGE', 'IMAGE_DIAGRAM', 'VIDEO'
    context_type = Column(String, nullable=False) 
    
    # Cột vạn năng kiểu JSONB: Lưu bất cứ thứ gì tùy theo context_type
    # - Nếu là 'READING_PASSAGE': Lưu chuỗi văn bản thô chứa ký tự đục lỗ.
    # - Nếu là 'AUDIO_SRT': Lưu cả một mảng danh sách các câu sub kèm timeline [ {start, end, text}, ... ]
    # - Nếu là 'IMAGE_DIAGRAM': Lưu link ảnh sơ đồ của IELTS.
    content = Column(JSON, nullable=False) 
    
    index = Column(Integer, nullable=False, default=0) # Thứ tự xuất hiện của bối cảnh này trong đề

    exam = relationship("Exam", back_populates="contexts")
    questions = relationship("ExamQuestion", back_populates="context")

class ExamQuestion(Base):
    """ BẢNG CÂU HỎI VẠN NĂNG CHO TOÀN BỘ CÁC CỰM ĐỀ THI """
    __tablename__ = "exam_questions"

    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    
    # Một câu hỏi CÓ THỂ thuộc về một bối cảnh (Part 3,4,6,7), hoặc đứng ĐỘC LẬP (Part 5) nếu để Null
    context_id = Column(String, ForeignKey("exam_contexts.id"), nullable=True)
    
    part = Column(Integer, nullable=False)          # Cột phân loại Part (1-7 của TOEIC, 1-4 của IELTS)
    question_number = Column(Integer, nullable=False) # Số thứ tự hiển thị (Câu 101, Câu 132...)
    
    # Định dạng câu trả lời: 'MULTIPLE_CHOICE', 'FILL_IN_THE_BLANK', 'ESSAY', 'RECORDING'
    question_type = Column(String, nullable=False, default="MULTIPLE_CHOICE") 
    
    content = Column(String, nullable=False)        # Nội dung câu hỏi
    options = Column(JSON, nullable=True)           # Mảng thô các đáp án (Dùng index 0,1,2,3 để random)
    correct_answer = Column(String, nullable=False) # Chữ cái đáp án chuẩn tương ứng ("A", "B"...)
    
    # Cột lưu trữ các biến đặc thù cho từng loại câu hỏi dưới dạng JSON
    # - Với Listening: Lưu {"audio_start": 12.5, "audio_end": 45.0}
    # - Với IELTS Điền từ: Lưu {"max_words": 3, "case_sensitive": False}
    additional_meta = Column(JSON, nullable=True) 

    exam = relationship("Exam", back_populates="questions")
    context = relationship("ExamContext", back_populates="questions")

class UserQuestionTag(Base):
    __tablename__ = "user_question_tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    question_id = Column(String, ForeignKey("exam_questions.id"), nullable=False)
    tag_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    dirty = Column(Integer, nullable=False, default=1) # 0: False, 1: True