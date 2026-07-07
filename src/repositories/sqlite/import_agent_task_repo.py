from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import inspect, select, text

from src.models.exam import ImportAgentTask
from src.repositories.sqlite import orm_models as orm
from src.repositories.sqlite.database import get_session

RETRY_DELAY_SECONDS = 60


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _datetime_to_db(value: datetime.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.isoformat()


def _datetime_from_db(value: str | datetime.datetime | None) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return value
    if not value:
        return _now()
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f%z")


def _optional_datetime_from_db(
    value: str | datetime.datetime | None,
) -> datetime.datetime | None:
    return _datetime_from_db(value) if value else None


def _task_from_orm(row: orm.ImportAgentTaskLocal) -> ImportAgentTask:
    r: Any = row
    return ImportAgentTask(
        id=r.id,
        status=r.status,
        payload=r.payload,
        ocr=str(getattr(r, "ocr", "") or ""),
        attempts=r.attempts,
        max_attempts=r.max_attempts,
        auto_retry=r.auto_retry,
        error_message=r.error_message,
        result=r.result,
        created_at=_datetime_from_db(r.created_at),
        updated_at=_datetime_from_db(r.updated_at),
        next_retry_at=_optional_datetime_from_db(r.next_retry_at),
    )


class ImportAgentTaskRepository:
    def __init__(self) -> None:
        self._ensure_ocr_column()

    def _ensure_ocr_column(self) -> None:
        session = get_session()
        try:
            inspector = inspect(session.bind)
            if not inspector.has_table("import_agent_tasks"):
                return
            columns = {
                column["name"]
                for column in inspector.get_columns("import_agent_tasks")
            }
            if "ocr" in columns:
                return
            session.execute(
                text(
                    "ALTER TABLE import_agent_tasks "
                    "ADD COLUMN ocr TEXT NOT NULL DEFAULT ''"
                )
            )
            session.commit()
        finally:
            session.close()

    def create_task(self, payload: dict, *, max_attempts: int = 3) -> ImportAgentTask:
        session = get_session()
        try:
            now = _datetime_to_db(_now())
            row = orm.ImportAgentTaskLocal(
                status="queued",
                payload=payload,
                ocr="",
                attempts=0,
                max_attempts=max_attempts,
                auto_retry=False,
                error_message="",
                result={},
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def list_tasks(self, limit: int = 100) -> list[ImportAgentTask]:
        session = get_session()
        try:
            stmt = (
                select(orm.ImportAgentTaskLocal)
                .order_by(orm.ImportAgentTaskLocal.created_at.desc())
                .limit(limit)
            )
            return [_task_from_orm(row) for row in session.scalars(stmt).all()]
        finally:
            session.close()

    def get_task(self, task_id: str) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            return _task_from_orm(row) if row else None
        finally:
            session.close()

    def mark_running(self, task_id: str) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row:
                return None
            row.status = "running"
            row.attempts += 1
            row.error_message = ""
            row.next_retry_at = None
            row.updated_at = _datetime_to_db(_now())
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def mark_succeeded(self, task_id: str, result: dict) -> None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row:
                return
            row.status = "succeeded"
            row.result = result
            row.error_message = ""
            row.next_retry_at = None
            row.updated_at = _datetime_to_db(_now())
            session.commit()
        finally:
            session.close()

    def mark_failed(
        self, task_id: str, error_message: str, *, retryable: bool
    ) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row:
                return None
            row.status = "failed"
            row.error_message = error_message
            row.next_retry_at = None
            row.updated_at = _datetime_to_db(_now())
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def queue_for_retry(self, task_id: str) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row or row.status == "running":
                return None
            row.status = "queued"
            row.auto_retry = False
            row.next_retry_at = _datetime_to_db(_now())
            row.updated_at = _datetime_to_db(_now())
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def update_payload(self, task_id: str, payload: dict) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row or row.status == "running":
                return None
            row.payload = payload
            row.updated_at = _datetime_to_db(_now())
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def update_ocr(self, task_id: str, ocr: str) -> ImportAgentTask | None:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row or row.status == "running":
                return None
            row.ocr = ocr
            row.updated_at = _datetime_to_db(_now())
            session.commit()
            session.refresh(row)
            return _task_from_orm(row)
        finally:
            session.close()

    def next_retryable_task(self) -> ImportAgentTask | None:
        session = get_session()
        try:
            now = _datetime_to_db(_now())
            stmt = (
                select(orm.ImportAgentTaskLocal)
                .where(orm.ImportAgentTaskLocal.status == "queued")
                .where(orm.ImportAgentTaskLocal.auto_retry.is_(True))
                .where(
                    orm.ImportAgentTaskLocal.attempts
                    < orm.ImportAgentTaskLocal.max_attempts
                )
                .where(
                    (orm.ImportAgentTaskLocal.next_retry_at.is_(None))
                    | (orm.ImportAgentTaskLocal.next_retry_at <= now)
                )
                .order_by(orm.ImportAgentTaskLocal.created_at.asc())
                .limit(1)
            )
            row = session.scalars(stmt).first()
            return _task_from_orm(row) if row else None
        finally:
            session.close()

    def delete_task(self, task_id: str) -> bool:
        session = get_session()
        try:
            row = session.get(orm.ImportAgentTaskLocal, task_id)
            if not row or row.status == "running":
                return False
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()
