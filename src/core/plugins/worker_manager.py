"""Lifecycle manager for plugin worker processes."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from src.core.plugins.plugin_worker import PluginWorker


class WorkerManager:
    """Create plugin workers lazily and stop them during shutdown."""

    def __init__(self) -> None:
        self._workers: Dict[Tuple[str, str], PluginWorker] = {}

    def get_worker(
        self,
        plugin_id: str,
        worker_id: str,
        executable_path: Path,
        args: Sequence[str] = (),
        cwd: Optional[Path] = None,
    ) -> PluginWorker:
        """Return a cached worker for a plugin."""
        key = (plugin_id, worker_id)
        worker = self._workers.get(key)
        if worker is None:
            worker = PluginWorker(executable_path=executable_path, args=args, cwd=cwd)
            self._workers[key] = worker
        return worker

    def shutdown_plugin(self, plugin_id: str) -> None:
        """Terminate all workers owned by one plugin."""
        for key, worker in list(self._workers.items()):
            if key[0] == plugin_id:
                worker.terminate()
                del self._workers[key]

    def shutdown_all(self) -> None:
        """Terminate all workers."""
        for worker in list(self._workers.values()):
            worker.terminate()
        self._workers.clear()
