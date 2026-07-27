import datetime
import json
from asyncio.log import logger
from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy import DateTime
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session
from supabase import Client

from src.config import SUPABASE_SCHEMA
from src.models.exam import ContextContent
from src.models.exam import ExamSrtChunk as ExamSrtChunkModel
from src.repositories.sqlite.database import get_session
from src.repositories.sqlite.orm_models import (
    Exam,
    ExamAttempt,
    ExamContext,
    ExamQuestion,
    MediaFile,
    UserAnswer,
    UserQuestionTag,
    Vocabulary,
)
from src.repositories.sqlite.sqlite_repo import _context_from_orm, _mediafile_from_orm
from src.repositories.supabase.auth import restore_session
from src.repositories.supabase.client import get_supabase_client
from src.utils.helpers import get_local_media_path
from src.utils.r2_service import download_media_file, upload_media_file

SYNC_MODELS = (
    Exam,
    ExamContext,
    ExamQuestion,
    UserQuestionTag,
    Vocabulary,
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
    schema = SUPABASE_SCHEMA.strip() or "public"
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
    data = {
        column.key: _serialize_value(getattr(row, column.key))
        for column in mapper.columns
    }
    if isinstance(row, Exam):
        data["srt_chunks"] = _serialize_exam_srt_chunks(data.get("srt_chunks"))
    return data


def _serialize_exam_srt_chunks(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return _normalize_exam_srt_chunk_payload(value)
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(decoded, list):
            return _normalize_exam_srt_chunk_payload(decoded)
    return []


def _deserialize_exam_srt_chunks(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return json.dumps(_serialize_exam_srt_chunks(value), ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(_normalize_exam_srt_chunk_payload(value), ensure_ascii=False)
    return ""


def _normalize_exam_srt_chunk_payload(value: list[Any]) -> list[dict[str, Any]]:
    chunks: list[ExamSrtChunkModel] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        chunks.append(ExamSrtChunkModel.model_validate(item))
    chunks.sort(key=lambda chunk: (chunk.index, chunk.start_time))
    return [chunk.model_dump(mode="json") for chunk in chunks]


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
    if model is Exam and "srt_chunks" in data:
        data["srt_chunks"] = _deserialize_exam_srt_chunks(data["srt_chunks"])
    return data


def _serialize_mediafile_row(row: MediaFile) -> dict[str, Any]:
    data = _serialize_row(row)
    data.pop("dirty", None)
    data.pop("is_deleted", None)
    return data


def _serialize_sync_row(row: Any, user_id: str) -> dict[str, Any]:
    data = _serialize_row(row)
    data.pop("dirty", None)
    if isinstance(row, UserQuestionTag):
        data["user_id"] = user_id
    return data


def _filter_sync_rows(session: Session, model: type, rows: list[Any]) -> list[Any]:
    if model is not UserQuestionTag:
        return rows

    context_ids = {context_id for (context_id,) in session.query(ExamContext.id).all()}
    return [
        row
        for row in rows
        if getattr(row, "context_id", None) in context_ids
    ]


def _get_dirty_rows(session: Session, model: type) -> list[Any]:
    dirty_column = getattr(model, "dirty")
    rows = (
        session.query(model)
        .filter(dirty_column.in_((True, 1)))
        .all()
    )
    return _filter_sync_rows(session, model, rows)


def _mark_rows_clean(rows: list[Any]) -> None:
    for row in rows:
        row.dirty = False


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


def _remote_mediafile_exists(
    supabase_client: Client,
    user_id: str,
    filename: str,
) -> bool:
    response = (
        supabase_client.table(MediaFile.__tablename__)
        .select("id")
        .eq("user_id", user_id)
        .eq("filename", filename)
        .range(0, 0)
        .execute()
    )
    return bool(response.data)


def _sync_dirty_mediafiles(
    session: Session,
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
        media = _mediafile_from_orm(row)
        if _remote_mediafile_exists(supabase_client, user_id, media.filename):
            row.dirty = False
            session.commit()
            continue
        if not media.is_deleted:
            local_media_path = get_local_media_path(media.filename)
            if not local_media_path.exists():
                continue
            try:
                upload_media_file(
                    local_path=local_media_path,
                    user_id=user_id,
                    filename=media.filename,
                )
            except Exception as e:
                logger.error(f"Failed to upload media file {media.filename}: {e}")
                continue

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
    session: Session,
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


def _rewrite_remote_media_references(session: Session) -> None:
    mediafiles = (
        session.query(MediaFile)
        .filter(MediaFile.is_deleted.is_(False))
        .order_by(MediaFile.created_at.asc())
        .all()
    )
    for mediafile in mediafiles:
        media = _mediafile_from_orm(mediafile)
        local_path = str(get_local_media_path(media.filename))
        contexts = (
            session.query(ExamContext)
            .filter(ExamContext.context_type == "IMAGE_DIAGRAM")
            .all()
        )
        for row in contexts:
            context = _context_from_orm(row)
            content = context.content if isinstance(context.content, ContextContent) else ContextContent(text="", image_filename="", image_path=None)
            if content.image_filename != media.filename:
                continue
            content.image_path = local_path
            context.content = content
    session.commit()


def _sync_remote_table_to_sqlite(
    session: Session,
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
        data = _deserialize_row(model, row)
        data["dirty"] = False
        session.merge(model(**data))
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
            local_rows = _get_dirty_rows(session, model)
            if _has_user_id_column(model):
                _apply_current_user_id(local_rows, user_id)
            rows = [_serialize_sync_row(row, user_id) for row in local_rows]
            _upsert_rows(
                supabase_client=supabase_client,
                table_name=table_name,
                rows=rows,
                batch_size=batch_size,
            )
            _mark_rows_clean(local_rows)
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
