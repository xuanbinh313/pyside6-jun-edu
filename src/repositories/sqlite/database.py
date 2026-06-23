from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///exams.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    from src.repositories.sqlite import orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()


def get_session():
    return SessionLocal()


def _ensure_schema_columns() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if not table_names:
        return

    exam_columns = (
        {column["name"] for column in inspector.get_columns("exams")}
        if "exams" in table_names
        else set()
    )
    context_columns = (
        {column["name"] for column in inspector.get_columns("exam_contexts")}
        if "exam_contexts" in table_names
        else set()
    )
    with engine.begin() as connection:
        if "audio_name" not in exam_columns:
            connection.execute(text("ALTER TABLE exams ADD COLUMN audio_name VARCHAR"))
            if "full_audio_url" in exam_columns:
                rows = connection.execute(
                    text(
                        "SELECT id, full_audio_url FROM exams "
                        "WHERE full_audio_url IS NOT NULL AND full_audio_url != ''"
                    )
                )
                for exam_id, full_audio_url in rows:
                    audio_name = Path(str(full_audio_url).replace("\\", "/")).name
                    connection.execute(
                        text("UPDATE exams SET audio_name = :audio_name WHERE id = :id"),
                        {"audio_name": audio_name, "id": exam_id},
                    )
        if "part" not in context_columns:
            connection.execute(
                text("ALTER TABLE exam_contexts ADD COLUMN part INTEGER NOT NULL DEFAULT 1")
            )
        if "additional_meta" not in context_columns:
            connection.execute(
                text(
                    "ALTER TABLE exam_contexts ADD COLUMN additional_meta JSON "
                    "DEFAULT '{\"audio_start\": 0.0, \"audio_end\": 0.0, \"note\": \"\"}'"
                )
            )
