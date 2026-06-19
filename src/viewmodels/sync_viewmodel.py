from PySide6.QtCore import QObject, QThread, Signal

from src.models.sync import sync_sqlite_to_supabase


class SyncWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            self.finished.emit(sync_sqlite_to_supabase())
        except Exception as exc:
            self.error.emit(str(exc))


class SyncViewModel(QObject):
    sync_started = Signal()
    sync_finished = Signal(list)
    sync_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_syncing = False
        self._worker = None

    def sync_to_supabase(self):
        if self.is_syncing:
            return

        self.is_syncing = True
        self.sync_started.emit()

        self._worker = SyncWorker()
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, results):
        self.is_syncing = False
        self.sync_finished.emit(results)
        self._worker = None

    def _on_error(self, message):
        self.is_syncing = False
        self.sync_failed.emit(message)
        self._worker = None
