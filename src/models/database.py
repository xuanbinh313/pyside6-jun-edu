from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///exams.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()

def _ensure_schema_columns():
    inspector = inspect(engine)
    if "exam_contexts" not in inspector.get_table_names():
        return
    context_columns = {column["name"] for column in inspector.get_columns("exam_contexts")}
    if "part" not in context_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE exam_contexts ADD COLUMN part INTEGER NOT NULL DEFAULT 1"))

def get_session():
    return SessionLocal()
