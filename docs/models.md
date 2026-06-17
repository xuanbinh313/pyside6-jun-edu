# Models Layer

> **Location:** `src/models/`  
> **Tech:** SQLAlchemy ORM · SQLite

---

## `src/models/database.py`

Database bootstrap module. Called once at app startup.

| Symbol | Type | Description |
|---|---|---|
| `DATABASE_URL` | `str` | `"sqlite:///exams.db"` — file stored in the working directory |
| `engine` | `Engine` | SQLAlchemy engine (echo off) |
| `SessionLocal` | `sessionmaker` | Factory for sessions (`autocommit=False`, `autoflush=False`) |
| `Base` | `DeclarativeBase` | ORM base class for all models |
| `init_db()` | function | Runs `Base.metadata.create_all()` — creates tables if missing |
| `get_session()` | function | Returns a new `SessionLocal()` session — **caller is responsible for closing** |

**Usage pattern:**
```python
from src.models.database import get_session

session = get_session()
try:
    # ... DB operations
    session.commit()
finally:
    session.close()
```

---

## `src/models/exam.py`

ORM model definitions.

### `Exam`

**Table:** `exams`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` (PK) | No | `uuid4()` | UUID primary key |
| `title` | `String` | No | — | Exam title |
| `description` | `String` | Yes | — | Optional description |
| `full_audio_url` | `String` | Yes | — | Absolute local file path **or** HTTP URL to audio |
| `duration_minutes` | `Integer` | No | `0` | Total exam duration |
| `is_published` | `Boolean` | No | `False` | Publish status |
| `user_id` | `String` | No | `""` | User identifier (defaults to `"local_user"` on import) |
| `created_at` | `DateTime` | — | `utcnow` | Creation timestamp |
| `updated_at` | `DateTime` | — | `utcnow` | Auto-updated on change |

**Relationships:**
- `srt_chunks` → `List[ExamSrtChunk]` (cascade: `all, delete-orphan`)

---

### `ExamSrtChunk`

**Table:** `exam_srt_chunks`

Represents a single subtitle segment (word/phrase) with audio timestamps.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `String` (PK) | No | UUID primary key |
| `exam_id` | `String` (FK → `exams.id`) | No | Parent exam reference |
| `index` | `Integer` | No | Ordering index within the exam |
| `start_time` | `Float` | No | Start position in seconds |
| `end_time` | `Float` | No | End position in seconds |
| `text` | `String` | No | Subtitle text content |
| `hint` | `String` | Yes | Optional hint/answer text |

**Relationships:**
- `exam` → `Exam` (back-populates `srt_chunks`)

---

### `generate_uuid()`

Helper returning `str(uuid.uuid4())` — used as the `default` for all primary key columns.
