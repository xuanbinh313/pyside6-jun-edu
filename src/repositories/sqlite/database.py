import importlib
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///exams.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    importlib.import_module("src.repositories.sqlite.orm_models")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    now = str(datetime.now(timezone.utc)).replace("'", "''")
    with engine.begin() as connection:
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
