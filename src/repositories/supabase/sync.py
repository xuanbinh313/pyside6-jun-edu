import datetime
import os
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv
from sqlalchemy.inspection import inspect
from supabase import Client

from src.repositories.supabase.auth import restore_session
from src.repositories.supabase.client import get_supabase_client
from src.repositories.sqlite.database import get_session
from src.repositories.sqlite.orm_models import (
    Exam,
    ExamAttempt,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    MediaFile,
    UserAnswer,
    UserQuestionTag,
)
from src.utils.helpers import get_local_media_path
from src.utils.r2_service import upload_media_file

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


def _get_supabase_schema() -> str:
    schema = os.getenv("SUPABASE_SCHEMA", "public").strip() or "public"
    get_supabase_client()
    return schema


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


def _serialize_mediafile_row(row: MediaFile) -> dict[str, Any]:
    data = _serialize_row(row)
    data.pop("dirty", None)
    data.pop("is_deleted", None)
    return data


def _chunked(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def _get_supabase_table_client(schema: str):
    client: Client = get_supabase_client()
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


def _current_supabase_user_id() -> str:
    auth_result = restore_session()
    if auth_result.user and auth_result.user.id:
        return auth_result.user.id
    raise SupabaseSyncError("Sign in to Supabase before syncing.")


def _has_user_id_column(model: type) -> bool:
    mapper = inspect(model)
    return "user_id" in {column.key for column in mapper.columns}


def _apply_current_user_id(rows: list[Any], user_id: str) -> None:
    for row in rows:
        if hasattr(row, "user_id"):
            row.user_id = user_id


def _sync_dirty_mediafiles(
    session,
    supabase_client,
    batch_size: int,
    user_id: str,
) -> TableSyncResult:
    dirty_rows = (
        session.query(MediaFile)
        .filter(MediaFile.dirty.is_(True))
        .order_by(MediaFile.created_at.asc())
        .all()
    )
    if not dirty_rows:
        return TableSyncResult(table_name=MediaFile.__tablename__, row_count=0)

    synced_count = 0
    for row in dirty_rows:
        row.user_id = user_id
        if not row.is_deleted:
            upload_media_file(
                local_path=get_local_media_path(row.filename),
                user_id=user_id,
                filename=row.filename,
            )

        mediafile_payload = _serialize_mediafile_row(row)
        _upsert_rows(
            supabase_client=supabase_client,
            table_name="mediafiles",
            rows=[mediafile_payload],
            batch_size=batch_size,
        )
        row.dirty = False
        session.commit()
        synced_count += 1

    return TableSyncResult(
        table_name=MediaFile.__tablename__,
        row_count=synced_count,
    )


def sync_sqlite_to_supabase(batch_size: int = 500) -> list[TableSyncResult]:
    """Upsert all local SQLite rows into matching Supabase tables."""
    user_id = _current_supabase_user_id()
    schema = _get_supabase_schema()
    supabase_client = _get_supabase_table_client(schema)

    session = get_session()
    try:
        results: list[TableSyncResult] = []
        results.append(
            _sync_dirty_mediafiles(
                session=session,
                supabase_client=supabase_client,
                batch_size=batch_size,
                user_id=user_id,
            )
        )
        for model in SYNC_MODELS:
            table_name = model.__tablename__
            local_rows = session.query(model).all()
            if _has_user_id_column(model):
                _apply_current_user_id(local_rows, user_id)
            rows = [_serialize_row(row) for row in local_rows]
            _upsert_rows(
                supabase_client=supabase_client,
                table_name=table_name,
                rows=rows,
                batch_size=batch_size,
            )
            session.commit()
            results.append(TableSyncResult(table_name=table_name, row_count=len(rows)))
        return results
    finally:
        session.close()
