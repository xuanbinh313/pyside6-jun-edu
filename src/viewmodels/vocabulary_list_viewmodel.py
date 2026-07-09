from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from src.models.exam import Vocabulary
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class VocabularyListViewModel(QObject):
    data_changed = Signal()
    error_occurred = Signal(str)

    def __init__(self, repo: IExamRepository | None = None) -> None:
        super().__init__()
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.vocabulary: list[Vocabulary] = []
        self._all_vocabulary: list[Vocabulary] = []
        self._search_query = ""

    def load_vocabulary(self) -> None:
        try:
            self._all_vocabulary = self.repo.list_vocabulary()
            self._apply_filter()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def set_search_query(self, query: str) -> None:
        self._search_query = query.strip().casefold()
        self._apply_filter()

    def update_status(self, vocab_id: str, status: int) -> None:
        try:
            self.repo.update_vocabulary_status(vocab_id, status)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def update_meaning(self, vocab_id: str, meaning: str) -> None:
        try:
            self.repo.update_vocabulary_meaning(vocab_id, meaning)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def delete_vocabulary(self, vocab_id: str) -> None:
        try:
            self.repo.delete_vocabulary(vocab_id)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _apply_filter(self) -> None:
        query = self._search_query
        self.vocabulary = [
            item
            for item in self._all_vocabulary
            if not query
            or query in item.word.casefold()
            or query in (item.meaning or "").casefold()
            or query in (item.source_text or "").casefold()
        ]
        self.data_changed.emit()
