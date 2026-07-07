import datetime
import os
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv
from sqlalchemy import DateTime
from sqlalchemy.inspection import inspect
from supabase import Client

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
from src.repositories.supabase.auth import restore_session
from src.repositories.supabase.client import get_supabase_client
from src.utils.helpers import get_local_media_path
from src.utils.r2_service import download_media_file, upload_media_file

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


def _deserialize_value(value: Any, column: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def _deserialize_row(model: type, row: dict[str, Any]) -> dict[str, Any]:
    mapper = inspect(model)
    columns = {column.key: column for column in mapper.columns}
    data = {
        key: _deserialize_value(value, columns[key])
        for key, value in row.items()
        if key in columns
    }
    if model is Exam and not data.get("audio_name") and row.get("full_audio_url"):
        data["audio_name"] = _path_leaf(str(row.get("full_audio_url") or ""))
    return data


def _serialize_mediafile_row(row: MediaFile) -> dict[str, Any]:
    data = _serialize_row(row)
    data.pop("dirty", None)
    data.pop("is_deleted", None)
    return data


def _chunked(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def _get_supabase_table_client(schema: str) -> Client:
    client: Client = get_supabase_client()
    if schema == "public":
        return client
    return client.schema(schema)


def _fetch_user_rows(
    supabase_client: Client,
    table_name: str,
    user_id: str,
    batch_size: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            supabase_client.table(table_name)
            .select("*")
            .eq("user_id", user_id)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = list(response.data or [])
        rows.extend(batch)
        if len(batch) < batch_size:
            return rows
        offset += batch_size


def _upsert_rows(
    supabase_client: Client,
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
    supabase_client: Client,
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


def _sync_remote_mediafiles_to_sqlite(
    session,
    supabase_client: Client,
    batch_size: int,
    user_id: str,
) -> TableSyncResult:
    rows = _fetch_user_rows(
        supabase_client=supabase_client,
        table_name=MediaFile.__tablename__,
        user_id=user_id,
        batch_size=batch_size,
    )
    downloaded_count = 0
    for row in rows:
        filename = str(row.get("filename", "") or "")
        if filename and not bool(row.get("is_deleted", False)):
            download_media_file(
                local_path=get_local_media_path(filename),
                user_id=user_id,
                filename=filename,
            )
            downloaded_count += 1

        data = _deserialize_row(MediaFile, row)
        data["dirty"] = False
        data.setdefault("is_deleted", False)
        session.merge(MediaFile(**data))
    session.commit()
    return TableSyncResult(
        table_name=MediaFile.__tablename__,
        row_count=downloaded_count,
    )


def _path_leaf(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _rewrite_remote_media_references(session) -> None:
    mediafiles = (
        session.query(MediaFile)
        .filter(MediaFile.is_deleted.is_(False))
        .order_by(MediaFile.created_at.asc())
        .all()
    )
    for mediafile in mediafiles:
        local_path = str(get_local_media_path(mediafile.filename))
        contexts = (
            session.query(ExamContext)
            .filter(ExamContext.context_type == "IMAGE_DIAGRAM")
            .all()
        )
        for context in contexts:
            content = context.content if isinstance(context.content, dict) else {}
            if content.get("image_filename") != mediafile.filename:
                continue
            content["image_path"] = local_path
            context.content = dict(content)
    session.commit()


def _sync_remote_table_to_sqlite(
    session,
    supabase_client: Client,
    model: type,
    batch_size: int,
    user_id: str,
) -> TableSyncResult:
    table_name = model.__tablename__
    rows = _fetch_user_rows(
        supabase_client=supabase_client,
        table_name=table_name,
        user_id=user_id,
        batch_size=batch_size,
    )
    for row in rows:
        session.merge(model(**_deserialize_row(model, row)))
    session.commit()
    return TableSyncResult(table_name=table_name, row_count=len(rows))


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


def sync_supabase_to_sqlite(batch_size: int = 500) -> list[TableSyncResult]:
    """Download Supabase rows and media into the local SQLite/temp store."""
    user_id = _current_supabase_user_id()
    schema = _get_supabase_schema()
    supabase_client: Client = _get_supabase_table_client(schema)

    session = get_session()
    try:
        results: list[TableSyncResult] = []
        results.append(
            _sync_remote_mediafiles_to_sqlite(
                session=session,
                supabase_client=supabase_client,
                batch_size=batch_size,
                user_id=user_id,
            )
        )
        for model in SYNC_MODELS:
            results.append(
                _sync_remote_table_to_sqlite(
                    session=session,
                    supabase_client=supabase_client,
                    model=model,
                    batch_size=batch_size,
                    user_id=user_id,
                )
            )
        _rewrite_remote_media_references(session)
        return results
    finally:
        session.close()
