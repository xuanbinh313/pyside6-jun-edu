from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from src.models.auth import (
    AuthResult,
    login_with_password,
    logout,
    register_with_password,
    restore_session,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func: Callable[[], Any]):
        super().__init__()
        self.func = func

    def run(self) -> None:
        try:
            self.finished.emit(self.func())
        except Exception as exc:
            self.error.emit(str(exc))


class AuthViewModel(QObject):
    state_changed = Signal()
    authenticated = Signal(str)
    info_message = Signal(str)
    error_message = Signal(str)
    logged_out = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_loading = False
        self.mode = "login"
        self.status_text = ""
        self.current_user_email = ""
        self._worker: AuthWorker | None = None

    @property
    def is_login_mode(self) -> bool:
        return self.mode == "login"

    def set_mode(self, mode: str) -> None:
        if mode not in {"login", "register"}:
            return
        self.mode = mode
        self.status_text = ""
        self.state_changed.emit()

    def toggle_mode(self) -> None:
        self.set_mode("register" if self.is_login_mode else "login")

    def check_saved_session(self) -> None:
        if self.is_loading:
            return
        self._start_worker(restore_session, self._on_auth_result, silent_error=True)

    def login(self, email: str, password: str) -> None:
        if not self._validate_credentials(email, password):
            return
        self._start_worker(
            lambda: login_with_password(email.strip(), password),
            self._on_auth_result,
        )

    def register(self, email: str, password: str, confirm_password: str) -> None:
        if not self._validate_credentials(email, password):
            return
        if password != confirm_password:
            self._set_error("Passwords do not match.")
            return
        self._start_worker(
            lambda: register_with_password(email.strip(), password),
            self._on_register_result,
        )

    def sign_out(self) -> None:
        if self.is_loading:
            return
        self._start_worker(logout, self._on_logout_finished)

    def _validate_credentials(self, email: str, password: str) -> bool:
        email = email.strip()
        if not email or not password:
            self._set_error("Email and password are required.")
            return False
        if not EMAIL_PATTERN.match(email):
            self._set_error("Enter a valid email address.")
            return False
        if len(password) < 6:
            self._set_error("Password must be at least 6 characters.")
            return False
        return True

    def _start_worker(
        self,
        func: Callable[[], Any],
        on_finished: Callable[[Any], None],
        *,
        silent_error: bool = False,
    ) -> None:
        self.is_loading = True
        self.status_text = "Working..."
        self.state_changed.emit()

        self._worker = AuthWorker(func)
        self._worker.finished.connect(on_finished)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.error.connect(
            lambda message: self._on_worker_error(message, silent_error=silent_error)
        )
        self._worker.error.connect(self._on_worker_done)
        self._worker.start()

    def _on_auth_result(self, result: AuthResult) -> None:
        if result.user is None:
            self.status_text = ""
            self.state_changed.emit()
            return

        self.current_user_email = result.user.email
        self.status_text = ""
        self.authenticated.emit(result.user.email)

    def _on_register_result(self, result: AuthResult) -> None:
        if result.user is not None and not result.requires_email_confirmation:
            self._on_auth_result(result)
            return

        message = result.message or "Registration successful. Check your email to verify your account."
        self.mode = "login"
        self.status_text = message
        self.info_message.emit(message)
        self.state_changed.emit()

    def _on_logout_finished(self, _result: Any) -> None:
        self.current_user_email = ""
        self.mode = "login"
        self.status_text = ""
        self.logged_out.emit()

    def _on_worker_error(self, message: str, *, silent_error: bool = False) -> None:
        self.status_text = ""
        if silent_error:
            return
        self.error_message.emit(_friendly_error(message))
        self.state_changed.emit()

    def _on_worker_done(self, *_args) -> None:
        self.is_loading = False
        self.state_changed.emit()

    def _set_error(self, message: str) -> None:
        self.status_text = message
        self.error_message.emit(message)
        self.state_changed.emit()


def _friendly_error(message: str) -> str:
    lowered = message.lower()
    if "invalid login credentials" in lowered:
        return "Invalid email or password."
    if "email not confirmed" in lowered or "not confirmed" in lowered:
        return "Please verify your email before logging in."
    if "already registered" in lowered or "already exists" in lowered:
        return "That email is already registered."
    if "connection" in lowered or "timeout" in lowered:
        return "Could not reach Supabase. Check your connection and try again."
    return message or "Authentication failed."
