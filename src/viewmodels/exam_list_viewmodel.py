from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from src.models.exam import Exam
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class ExamListViewModel(QObject):
    data_changed = Signal()

    def __init__(self, repo: IExamRepository | None = None):
        super().__init__()
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.exams: list[Exam] = []
        self._search_query: str = ""

    def load_exams(self):
        self.exams = self.repo.list_exams(self._search_query)
        self.data_changed.emit()

    def set_search_query(self, query: str):
        self._search_query = query
        self.load_exams()

    def delete_exam(self, exam_id: str):
        self.repo.delete_exam(exam_id)
        self.load_exams()
