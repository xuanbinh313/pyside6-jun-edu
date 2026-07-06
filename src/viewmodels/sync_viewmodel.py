from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal
from src.repositories.supabase.sync import (
    sync_sqlite_to_supabase,
    sync_supabase_to_sqlite,
)


class SyncWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, sync_func: Callable[[], list[str]]):
        super().__init__()
        self.sync_func = sync_func

    def run(self):
        try:
            self.finished.emit(self.sync_func())
        except Exception as exc:
            self.error.emit(str(exc))


class SyncViewModel(QObject):
    sync_started = Signal()
    sync_finished = Signal(list)
    sync_failed = Signal(str)
    local_sync_started = Signal()
    local_sync_finished = Signal(list)
    local_sync_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_syncing = False
        self._worker = None

    def sync_to_supabase(self):
        if self.is_syncing:
            return

        self.is_syncing = True
        self.sync_started.emit()

        self._worker = SyncWorker(sync_sqlite_to_supabase)
        self._worker.finished.connect(self._on_supabase_finished)
        self._worker.error.connect(self._on_supabase_error)
        self._worker.start()

    def sync_to_local(self):
        if self.is_syncing:
            return

        self.is_syncing = True
        self.local_sync_started.emit()

        self._worker = SyncWorker(sync_supabase_to_sqlite)
        self._worker.finished.connect(self._on_local_finished)
        self._worker.error.connect(self._on_local_error)
        self._worker.start()

    def _on_supabase_finished(self, results):
        self.is_syncing = False
        self.sync_finished.emit(results)
        self._worker = None

    def _on_supabase_error(self, message):
        self.is_syncing = False
        self.sync_failed.emit(message)
        self._worker = None

    def _on_local_finished(self, results):
        self.is_syncing = False
        self.local_sync_finished.emit(results)
        self._worker = None

    def _on_local_error(self, message):
        self.is_syncing = False
        self.local_sync_failed.emit(message)
        self._worker = None
