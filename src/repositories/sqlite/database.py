import importlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///exams.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    importlib.import_module("src.repositories.sqlite.orm_models")
    Base.metadata.create_all(bind=engine)
    now = str(datetime.now(timezone.utc)).replace("'", "''")
    with engine.begin() as connection:
        inspector = inspect(connection)
        exam_columns = {column["name"] for column in inspector.get_columns("exams")}
        if "srt_chunks" not in exam_columns:
            connection.execute(text("ALTER TABLE exams ADD COLUMN srt_chunks TEXT"))

        if inspector.has_table("exam_attempts"):
            attempt_columns = {
                column["name"] for column in inspector.get_columns("exam_attempts")
            }
            if "additional_meta" not in attempt_columns:
                connection.execute(
                    text(
                        "ALTER TABLE exam_attempts "
                        "ADD COLUMN additional_meta JSON NOT NULL DEFAULT '{}'"
                    )
                )

        if inspector.has_table("exam_srt_chunks"):
            rows = (
                connection.execute(
                    text(
                        "SELECT exam_id, id, \"index\", start_time, end_time, text, "
                        "hint, user_id, additional_meta "
                        "FROM exam_srt_chunks "
                        "ORDER BY exam_id ASC, \"index\" ASC, start_time ASC"
                    )
                )
                .mappings()
                .all()
            )
            chunks_by_exam: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                exam_id = str(row["exam_id"])
                additional_meta = row["additional_meta"]
                if isinstance(additional_meta, str):
                    try:
                        additional_meta = json.loads(additional_meta)
                    except json.JSONDecodeError:
                        additional_meta = {"words": []}
                if not isinstance(additional_meta, dict):
                    additional_meta = {"words": []}
                chunks_by_exam.setdefault(exam_id, []).append(
                    {
                        "id": row["id"],
                        "exam_id": exam_id,
                        "index": row["index"],
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "text": row["text"],
                        "note": "",
                        "hint": row["hint"],
                        "user_id": row["user_id"],
                        "additional_meta": additional_meta,
                    }
                )
            for exam_id, chunks in chunks_by_exam.items():
                connection.execute(
                    text(
                        "UPDATE exams SET srt_chunks = :srt_chunks "
                        "WHERE id = :exam_id "
                        "AND (srt_chunks IS NULL OR srt_chunks = '')"
                    ),
                    {
                        "exam_id": exam_id,
                        "srt_chunks": json.dumps(chunks, ensure_ascii=False),
                    },
                )

        vocabulary_columns = {
            column["name"] for column in inspector.get_columns("vocabulary")
        }
        vocabulary_migrations = {
            "meaning": "ALTER TABLE vocabulary ADD COLUMN meaning VARCHAR",
            "status": (
                "ALTER TABLE vocabulary ADD COLUMN "
                "status INTEGER NOT NULL DEFAULT 1"
            ),
            "source_text": "ALTER TABLE vocabulary ADD COLUMN source_text VARCHAR",
            "ord": "ALTER TABLE vocabulary ADD COLUMN ord INTEGER NOT NULL DEFAULT 0",
            "due_at": (
                "ALTER TABLE vocabulary ADD COLUMN "
                f"due_at VARCHAR NOT NULL DEFAULT '{now}'"
            ),
            "stability": (
                "ALTER TABLE vocabulary ADD COLUMN "
                "stability FLOAT NOT NULL DEFAULT 0.0"
            ),
            "difficulty": (
                "ALTER TABLE vocabulary ADD COLUMN "
                "difficulty FLOAT NOT NULL DEFAULT 0.0"
            ),
            "reps": "ALTER TABLE vocabulary ADD COLUMN reps INTEGER NOT NULL DEFAULT 0",
            "lapses": (
                "ALTER TABLE vocabulary ADD COLUMN lapses INTEGER NOT NULL DEFAULT 0"
            ),
            "step": "ALTER TABLE vocabulary ADD COLUMN step INTEGER",
            "data": (
                "ALTER TABLE vocabulary ADD COLUMN "
                "data JSON NOT NULL DEFAULT '{}'"
            ),
            "state": (
                "ALTER TABLE vocabulary ADD COLUMN state INTEGER NOT NULL DEFAULT 0"
            ),
            "last_review_at": (
                "ALTER TABLE vocabulary ADD COLUMN last_review_at VARCHAR"
            ),
            "updated_at": (
                "ALTER TABLE vocabulary ADD COLUMN "
                f"updated_at VARCHAR NOT NULL DEFAULT '{now}'"
            ),
        }
        for column_name, statement in vocabulary_migrations.items():
            if column_name not in vocabulary_columns:
                connection.execute(text(statement))

        for table in Base.metadata.sorted_tables:
            if "dirty" not in table.columns:
                continue
            table_columns = {
                column["name"] for column in inspector.get_columns(table.name)
            }
            if "dirty" not in table_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table.name} "
                        "ADD COLUMN dirty BOOLEAN NOT NULL DEFAULT 1"
                    )
                )


def get_session():
    return SessionLocal()
