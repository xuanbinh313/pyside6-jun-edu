
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///exams.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("vocabulary")}
    migrations = {
        "meaning": "ALTER TABLE vocabulary ADD COLUMN meaning VARCHAR",
        "status": "ALTER TABLE vocabulary ADD COLUMN status INTEGER NOT NULL DEFAULT 1",
    }
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))

def get_session():
    return SessionLocal()
