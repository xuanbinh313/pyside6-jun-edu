from PySide6.QtCore import QObject, Signal
from src.models.database import get_session
from src.models.exam import Exam

class ExamListViewModel(QObject):
    data_changed = Signal()

    def __init__(self):
        super().__init__()
        self.exams = []
        self._search_query = ""

    def load_exams(self):
        session = get_session()
        query = session.query(Exam)
        if self._search_query:
            query = query.filter(Exam.title.ilike(f"%{self._search_query}%"))
        self.exams = query.all()
        session.close()
        self.data_changed.emit()

    def set_search_query(self, query):
        self._search_query = query
        self.load_exams()

    def delete_exam(self, exam_id):
        session = get_session()
        exam = session.query(Exam).filter(Exam.id == exam_id).first()
        if exam:
            session.delete(exam)
            session.commit()
        session.close()
        self.load_exams()
