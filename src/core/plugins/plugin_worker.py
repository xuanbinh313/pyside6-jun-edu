"""Line-delimited JSON worker process support for plugins."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.core.plugins.exceptions import WorkerError


class PluginWorker:
    """Manage one long-running JSON-lines subprocess."""

    def __init__(
        self,
        executable_path: Path,
        args: Sequence[str] = (),
        cwd: Optional[Path] = None,
    ) -> None:
        self._executable_path = executable_path
        self._args = list(args)
        self._cwd = cwd
        self._process: Optional[subprocess.Popen[str]] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Return True when the worker process is alive."""
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Start the worker if it is not already running."""
        if self.is_running:
            return
        if not self._executable_path.is_file():
            raise WorkerError(f"Worker executable does not exist: {self._executable_path}")

        try:
            self._process = subprocess.Popen(
                [str(self._executable_path), *self._args],
                cwd=str(self._cwd) if self._cwd is not None else None,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
        except OSError as exc:
            raise WorkerError(f"Failed to start worker: {exc}") from exc

    def send_request(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Send a JSON request and wait for one JSON response line."""
        self.start()
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise WorkerError("Worker process is not available")

        with self._lock:
            try:
                process.stdin.write(json.dumps(dict(payload)) + "\n")
                process.stdin.flush()
                response_line = process.stdout.readline()
            except OSError as exc:
                raise WorkerError(f"Worker communication failed: {exc}") from exc

        if not response_line:
            raise WorkerError("Worker exited without returning a response")

        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as exc:
            raise WorkerError(f"Worker returned invalid JSON: {exc}") from exc
        if not isinstance(response, dict):
            raise WorkerError("Worker response must be a JSON object")
        return response

    def terminate(self) -> None:
        """Terminate the worker process."""
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._process = None
