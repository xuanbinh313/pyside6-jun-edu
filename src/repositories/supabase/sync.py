import datetime
import os
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv
from sqlalchemy.inspection import inspect
from supabase import Client, create_client

from src.repositories.sqlite.database import get_session
from src.repositories.sqlite.orm_models import (
    Exam,
    ExamAttempt,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    UserAnswer,
    UserQuestionTag,
)

load_dotenv()

SYNC_MODELS = (
    Exam,
    ExamSrtChunk,
    ExamContext,
    ExamQuestion,
    UserQuestionTag,
    ExamAttempt,
    UserAnswer,
)


@dataclass(frozen=True)
class TableSyncResult:
    table_name: str
    row_count: int


class SupabaseSyncError(Exception):
    """Raised when local data cannot be synced to Supabase."""


def _get_supabase_settings() -> tuple[str, str, str]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    schema = os.getenv("SUPABASE_SCHEMA", "public").strip() or "public"

    if not url:
        raise SupabaseSyncError("SUPABASE_URL is missing from .env.")
    if not key:
        raise SupabaseSyncError(
            "SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is missing from .env."
        )

    return url, key, schema


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def _serialize_row(row: Any) -> dict[str, Any]:
    mapper = inspect(row.__class__)
    return {
        column.key: _serialize_value(getattr(row, column.key))
        for column in mapper.columns
    }


def _chunked(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(rows), size):
        yield rows[index:index + size]


def _get_supabase_table_client(
    supabase_url: str,
    supabase_key: str,
    schema: str,
):
    client: Client = create_client(supabase_url, supabase_key)
    if schema == "public":
        return client
    return client.schema(schema)


def _upsert_rows(
    supabase_client,
    table_name: str,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> None:
    if not rows:
        return

    for batch in _chunked(rows, batch_size):
        supabase_client.table(table_name).upsert(
            batch,
            on_conflict="id",
        ).execute()


def sync_sqlite_to_supabase(batch_size: int = 500) -> list[TableSyncResult]:
    """Upsert all local SQLite rows into matching Supabase tables."""
    supabase_url, supabase_key, schema = _get_supabase_settings()
    supabase_client = _get_supabase_table_client(supabase_url, supabase_key, schema)

    session = get_session()
    try:
        results: list[TableSyncResult] = []
        for model in SYNC_MODELS:
            table_name = model.__tablename__
            rows = [_serialize_row(row) for row in session.query(model).all()]
            _upsert_rows(
                supabase_client=supabase_client,
                table_name=table_name,
                rows=rows,
                batch_size=batch_size,
            )
            results.append(TableSyncResult(table_name=table_name, row_count=len(rows)))
        return results
    finally:
        session.close()
