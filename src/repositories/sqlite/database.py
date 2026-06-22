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
    if "exam_contexts" not in inspector.get_table_names():
        return

    context_columns = {column["name"] for column in inspector.get_columns("exam_contexts")}
    with engine.begin() as connection:
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
