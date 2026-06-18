from PySide6.QtCore import QObject, Signal
from src.models.database import get_session
from src.models.exam import Exam, ExamSrtChunk

class ExamDetailsViewModel(QObject):
    data_loaded = Signal()
    data_saved = Signal()

    def __init__(self, exam_id=None):
        super().__init__()
        self.exam_id = exam_id
        self.exam = None
        self.srt_chunks = []
        self.questions = []

    def load_exam(self):
        session = get_session()
        if self.exam_id:
            self.exam = session.query(Exam).filter(Exam.id == self.exam_id).first()
            if self.exam:
                self.srt_chunks = self.exam.srt_chunks
                self.questions = self.exam.questions
        else:
            self.exam = Exam(title="")
            self.srt_chunks = []
            self.questions = []
        # Detach or map to simple DTO if needed, but for local desktop, we can use the object properties directly
        session.expunge_all()
        session.close()
        self.data_loaded.emit()

    def save_exam(self, title, description, duration_minutes, is_published):
        session = get_session()
        exam = None
        if self.exam_id:
            exam = session.query(Exam).filter(Exam.id == self.exam_id).first()
        
        if not exam:
            exam = Exam()
            session.add(exam)

        exam.title = title
        exam.description = description
        exam.duration_minutes = duration_minutes
        exam.is_published = is_published
        
        session.commit()
        self.exam_id = exam.id
        session.close()
        self.data_saved.emit()

    def save_chunks(self):
        """Persist all current srt_chunks to SQLite, replacing previous ones for this exam."""
        if not self.exam_id:
            return

        session = get_session()
        try:
            session.query(ExamSrtChunk).filter(
                ExamSrtChunk.exam_id == self.exam_id
            ).delete()

            for chunk in self.srt_chunks:
                new_chunk = ExamSrtChunk(
                    exam_id=self.exam_id,
                    index=chunk.index,
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    text=chunk.text,
                    hint=getattr(chunk, 'hint', None),
                )
                session.add(new_chunk)

            session.commit()
        finally:
            session.close()

    def duplicate_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        max_idx = max((c.index for c in self.srt_chunks), default=0)
        
        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=max_idx + 1,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text
        )
        self.srt_chunks.insert(list_idx + 1, new_chunk)
        return list_idx + 1, new_chunk

    def merge_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        if list_idx >= len(self.srt_chunks) - 1:
            return None, None
            
        next_chunk = self.srt_chunks[list_idx + 1]
        
        chunk.text = f"{chunk.text} {next_chunk.text}"
        chunk.end_time = next_chunk.end_time
        
        self.srt_chunks.pop(list_idx + 1)
        return list_idx, next_chunk
