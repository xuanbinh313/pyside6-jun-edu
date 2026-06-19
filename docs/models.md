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

## `src/models/sync.py`

Supabase sync module. Called by `SyncViewModel` when the user chooses **Sync to Supabase** from the main menu.

### Environment

Create or update `.env` in the project root:

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Recommended | Service role key for trusted desktop sync writes |
| `SUPABASE_KEY` | Fallback | Used only when `SUPABASE_SERVICE_ROLE_KEY` is not set |
| `SUPABASE_SCHEMA` | No | Supabase schema, defaults to `public` |

### Behavior

| Symbol | Type | Description |
|---|---|---|
| `SYNC_MODELS` | `tuple[type]` | Ordered ORM models synced to Supabase |
| `TableSyncResult` | dataclass | Contains `table_name` and `row_count` for UI summary |
| `SupabaseSyncError` | exception | Raised when required `.env` settings are missing |
| `sync_sqlite_to_supabase()` | function | Reads all SQLite rows and upserts them into matching Supabase tables via the `supabase` client library |

Supabase table names and columns must match the SQLAlchemy table names and column keys. Rows are upserted by primary key `id`, so matching remote rows are updated and missing rows are inserted.

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
