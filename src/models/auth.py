from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.models.supabase_client import get_supabase_client

SESSION_FILE = Path.home() / ".jun_edu" / "auth_session.json"


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str


@dataclass(frozen=True)
class AuthResult:
    user: AuthUser | None
    message: str = ""
    requires_email_confirmation: bool = False


def _session_payload(session: Any) -> dict[str, str]:
    access_token = getattr(session, "access_token", "") or ""
    refresh_token = getattr(session, "refresh_token", "") or ""
    if not access_token or not refresh_token:
        return {}
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def _auth_user(user: Any) -> AuthUser | None:
    if user is None:
        return None
    return AuthUser(
        id=str(getattr(user, "id", "") or ""),
        email=str(getattr(user, "email", "") or ""),
    )


def _save_session(session: Any) -> None:
    payload = _session_payload(session)
    if not payload:
        return

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(payload), encoding="utf-8")
    if os.name != "nt":
        SESSION_FILE.chmod(0o600)


def load_session_tokens() -> dict[str, str]:
    if not SESSION_FILE.exists():
        return {}

    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    access_token = str(data.get("access_token", "") or "")
    refresh_token = str(data.get("refresh_token", "") or "")
    if not access_token or not refresh_token:
        return {}
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def clear_session_tokens() -> None:
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def login_with_password(email: str, password: str) -> AuthResult:
    response = get_supabase_client().auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    _save_session(response.session)
    return AuthResult(user=_auth_user(response.user))


def register_with_password(email: str, password: str) -> AuthResult:
    response = get_supabase_client().auth.sign_up(
        {"email": email, "password": password}
    )
    _save_session(response.session)
    return AuthResult(
        user=_auth_user(response.user),
        message="Registration successful. Check your email to verify your account.",
        requires_email_confirmation=response.session is None,
    )


def restore_session() -> AuthResult:
    tokens = load_session_tokens()
    if not tokens:
        return AuthResult(user=None, message="No saved session.")

    client = get_supabase_client()
    try:
        response = client.auth.set_session(
            tokens["access_token"],
            tokens["refresh_token"],
        )
    except Exception:
        clear_session_tokens()
        raise

    _save_session(response.session)
    user = _auth_user(response.user)
    if user is not None:
        return AuthResult(user=user)

    try:
        user_response = client.auth.get_user()
    except Exception:
        clear_session_tokens()
        raise

    user = _auth_user(user_response.user)
    if user is None:
        clear_session_tokens()
    return AuthResult(user=user)


def logout() -> None:
    try:
        get_supabase_client().auth.sign_out()
    finally:
        clear_session_tokens()
