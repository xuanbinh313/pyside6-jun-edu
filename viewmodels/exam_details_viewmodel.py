from PySide6.QtCore import QObject, Signal
from models.database import get_session
from models.exam import Exam, ExamSrtChunk

class ExamDetailsViewModel(QObject):
    data_loaded = Signal()
    data_saved = Signal()

    def __init__(self, exam_id=None):
        super().__init__()
        self.exam_id = exam_id
        self.exam = None
        self.srt_chunks = []

    def load_exam(self):
        session = get_session()
        if self.exam_id:
            self.exam = session.query(Exam).filter(Exam.id == self.exam_id).first()
            if self.exam:
                self.srt_chunks = self.exam.srt_chunks
        else:
            self.exam = Exam(title="")
            self.srt_chunks = []
        # Detach or map to simple DTO if needed, but for local desktop, we can use the object properties directly
        session.expunge_all()
        session.close()
        self.data_loaded.emit()

    def save_exam(self, title, description, duration_minutes, is_published):
        session = get_session()
        if self.exam_id:
            exam = session.query(Exam).filter(Exam.id == self.exam_id).first()
        else:
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

