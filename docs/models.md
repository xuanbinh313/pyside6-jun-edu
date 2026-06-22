# Models Layer

> **Location:** `src/models/`
> **Tech:** SQLAlchemy ORM, SQLite, optional Supabase sync

The models layer owns database bootstrap, ORM table declarations, persistence
shape, and sync serialization. It must stay free of Qt imports.

## Session Usage

Database sessions come from `src.models.database.get_session()`. The caller owns
transaction scope and must close the session.

```python
from src.models.database import get_session

session = get_session()
try:
    # query, add, update, delete
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

ViewModels should load ORM objects, expunge or convert them when they need to
outlive the session, and avoid passing open sessions into views.

## `src/models/database.py`

Database bootstrap module. `init_db()` is called at app startup.

| Symbol | Type | Description |
|---|---|---|
| `DATABASE_URL` | `str` | `sqlite:///exams.db`; the database file is created in the working directory. |
| `engine` | `Engine` | SQLAlchemy engine with `echo=False`. |
| `SessionLocal` | `sessionmaker` | Session factory with `autocommit=False` and `autoflush=False`. |
| `Base` | declarative base | ORM base used by all model classes. |
| `init_db()` | function | Runs `Base.metadata.create_all(bind=engine)`, then applies small compatibility schema patches. |
| `_ensure_schema_columns()` | function | Adds `exam_contexts.part INTEGER NOT NULL DEFAULT 1` when upgrading an older local database missing that column. |
| `get_session()` | function | Returns a new `SessionLocal()` session. |

`_ensure_schema_columns()` is intentionally narrow. Add future schema patches
there only when they are safe for already-created SQLite databases.

## `src/models/supabase_client.py`

Shared Supabase client factory for auth/API use.

| Environment Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL. Trailing slashes are trimmed. |
| `SUPABASE_ANON_KEY` | Yes | Public anon key used by desktop auth. |
| `SUPABASE_KEY` | Fallback | Used when `SUPABASE_ANON_KEY` is not set. |

`get_supabase_client()` is cached so views and viewmodels share one client.

## `src/models/auth.py`

Supabase auth helpers used by `AuthViewModel`. This module owns local token
persistence in `~/.jun_edu/auth_session.json`.

| Function | Description |
|---|---|
| `login_with_password(email, password)` | Calls `supabase.auth.sign_in_with_password()`, saves returned tokens, and returns an `AuthResult`. |
| `register_with_password(email, password)` | Calls `supabase.auth.sign_up()`, saves tokens when Supabase returns a session, and reports email-confirmation state. |
| `restore_session()` | Loads saved tokens, restores them into the Supabase client, verifies the user, and clears invalid tokens. |
| `logout()` | Calls `supabase.auth.sign_out()` and clears local tokens. |

## `src/models/exam.py`

ORM model definitions for exams, transcript chunks, contexts, questions, tags,
attempts, and per-question answers.

`generate_uuid()` returns `str(uuid.uuid4())` and is used as the default primary
key factory.

### `Exam`

**Table:** `exams`

Top-level exam record.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `title` | `String` | No | - | Exam title. |
| `description` | `String` | Yes | - | Optional description. |
| `full_audio_url` | `String` | Yes | - | Local file path or HTTP URL for full exam audio. |
| `duration_minutes` | `Integer` | No | `0` | Total real-test duration. |
| `is_published` | `Boolean` | No | `False` | Publish flag. |
| `user_id` | `String` | Yes | - | Owner/user identifier. |
| `created_at` | `DateTime` | Yes | current UTC time | Creation timestamp. |
| `updated_at` | `DateTime` | Yes | current UTC time | Updated automatically on ORM update. |

**Relationships:**

| Relationship | Target | Cascade | Description |
|---|---|---|---|
| `srt_chunks` | `list[ExamSrtChunk]` | `all, delete-orphan` | Editable transcript/audio segments. |
| `contexts` | `list[ExamContext]` | `all, delete-orphan` | Grouped question contexts ordered by part/index. |
| `attempts` | `list[ExamAttempt]` | `all, delete-orphan` | Saved learner attempts. |

### `ExamSrtChunk`

**Table:** `exam_srt_chunks`

One transcript segment with audio timing.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `exam_id` | `String` FK -> `exams.id` | No | - | Parent exam. |
| `index` | `Integer` | No | - | Ordering index within the exam transcript. |
| `start_time` | `Float` | No | - | Start time in seconds. |
| `end_time` | `Float` | No | - | End time in seconds. |
| `text` | `String` | No | - | Transcript text. |
| `hint` | `String` | Yes | - | Optional hint/answer text. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |

**Relationships:**

| Relationship | Target | Description |
|---|---|---|
| `exam` | `Exam` | Back-populates `Exam.srt_chunks`. |

### `ExamContext`

**Table:** `exam_contexts`

Shared context for one or more questions. This is where TOEIC/IELTS part and
passage/diagram/audio context live. Standalone questions still use a context,
usually one `STANDALONE` context per question.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `exam_id` | `String` FK -> `exams.id` | No | - | Parent exam. |
| `part` | `Integer` | No | `1` | Exam part/section. Stored on context, not on question. |
| `context_type` | `String` | No | - | Context kind, such as `READING_PASSAGE`, `AUDIO_SRT`, `IMAGE_DIAGRAM`, or `STANDALONE`. |
| `content` | `JSON` | No | - | Context payload. Commonly a dict. |
| `index` | `Integer` | No | `0` | Ordering within the part/exam. |
| `additional_meta` | `JSON` | Yes | `{"audio_start": 0.0, "audio_end": 0.0, "note": ""}` | Context-level audio timing and optional context note. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |

**Common `content` shapes:**

| `context_type` | Shape |
|---|---|
| `READING_PASSAGE` | `{"text": "Passage text with [[131]] placeholders"}` |
| `IMAGE_DIAGRAM` | `{"text": "Diagram description", "image_data_url": "data:image/..."}` |
| `STANDALONE` | `{"text": ""}` |

**Relationships:**

| Relationship | Target | Cascade | Description |
|---|---|---|---|
| `exam` | `Exam` | - | Back-populates `Exam.contexts`. |
| `questions` | `list[ExamQuestion]` | default SQLAlchemy cascade only | Questions assigned to this context. |

### `AdditionalMeta`

`TypedDict` describing the expected JSON keys stored in
`ExamContext.additional_meta`.

| Key | Type | Description |
|---|---|---|
| `audio_start` | `float` | Optional clip start in seconds. |
| `audio_end` | `float` | Optional clip end in seconds. |
| `note` | `str` | Explanation or teacher note. |

### `QuestionAdditionalMeta`

`TypedDict` describing the expected JSON keys stored in
`ExamQuestion.additional_meta`.

| Key | Type | Description |
|---|---|---|
| `note` | `str` | Explanation or teacher note for the question answer. |

### `ExamQuestion`

**Table:** `exam_questions`

Question row linked to an `ExamContext`.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `context_id` | `String` FK -> `exam_contexts.id` | No | - | Parent context. |
| `question_number` | `Integer` | No | - | Printed question number. |
| `question_type` | `String` | No | `MULTIPLE_CHOICE` | Type/category used by rendering and analytics. |
| `content` | `String` | No | - | Question stem. |
| `options` | `JSON` | Yes | `[]` | Canonical option texts in original A-D order. Some import code may pass a JSON string; consumers normalize both list and string. |
| `correct_answer` | `String` | No | - | Canonical answer label, usually `A`, `B`, `C`, or `D`. |
| `additional_meta` | `JSON` | Yes | `{"note": ""}` | Answer explanation metadata. Legacy rows may still contain audio timing; helpers fall back to it when context timing is missing. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |

**Relationships:**

| Relationship | Target | Cascade | Description |
|---|---|---|---|
| `context` | `ExamContext` or `None` | - | Back-populates `ExamContext.questions`. |
| `answers` | `list[UserAnswer]` | default SQLAlchemy cascade only | Attempt answers for this question. |

Answer options are canonical. During an exam attempt, displayed options may be
shuffled, but `UserAnswer.user_choice` stores the original canonical letter.

### `UserQuestionTag`

**Table:** `user_question_tags`

Per-user tag assigned to a question, used by practice filtering.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |
| `question_id` | `String` FK -> `exam_questions.id` | No | - | Tagged question. |
| `tag_name` | `String` | No | - | Free-form tag label. |
| `created_at` | `DateTime` | Yes | current UTC time | Creation timestamp. |
| `dirty` | `Integer` | No | `1` | Sync/review marker. |

There is no explicit ORM relationship on this class today. Code joins it to
`ExamQuestion` manually.

### `ExamAttempt`

**Table:** `exam_attempts`

One completed learner run for an exam.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |
| `exam_id` | `String` FK -> `exams.id` | No | - | Parent exam. |
| `total_correct` | `Integer` | No | `0` | Number of correct answers at submission time. |
| `total_questions` | `Integer` | No | `0` | Number of active questions submitted. |
| `final_score` | `Float` | Yes | - | Percent score, or `None` when no questions. |
| `duration_seconds` | `Integer` | No | `0` | Elapsed attempt duration. |
| `created_at` | `DateTime` | Yes | current UTC time | Submission timestamp. |
| `dirty` | `Boolean` | No | `False` | Sync/review marker. |

**Relationships:**

| Relationship | Target | Cascade | Description |
|---|---|---|---|
| `exam` | `Exam` | - | Back-populates `Exam.attempts`. |
| `answers` | `list[UserAnswer]` | `all, delete-orphan` | Per-question answer rows for the attempt. |

`ExamTakeViewModel.complete_test()` creates the attempt and all related
`UserAnswer` rows in one transaction.

### `UserAnswer`

**Table:** `user_answers`

Per-question answer stored for one attempt.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `String` PK | No | `generate_uuid()` | UUID primary key. |
| `attempt_id` | `String` FK -> `exam_attempts.id` with `ondelete="CASCADE"` | No | - | Parent attempt. |
| `question_id` | `String` FK -> `exam_questions.id` | No | - | Answered question. |
| `user_choice` | `String` | Yes | - | Canonical selected letter, or `NULL` when unanswered/skipped. |
| `is_correct` | `Boolean` | No | - | Correctness flag; indexed. Unanswered answers are stored as `False`. |
| `user_id` | `String` | Yes | - | User identifier; indexed. |
| `dirty` | `Boolean` | No | `False` | Sync/review marker. |

**Relationships:**

| Relationship | Target | Description |
|---|---|---|
| `attempt` | `ExamAttempt` | Back-populates `ExamAttempt.answers`. |
| `question` | `ExamQuestion` | Back-populates `ExamQuestion.answers`. |

Analytics distinguish wrong and skipped answers by checking both fields:

```python
skipped = user_answer.user_choice is None
wrong = not user_answer.is_correct and user_answer.user_choice is not None
```

## `src/models/sync.py`

Supabase sync module. It is called by the sync ViewModel when the user chooses
to sync local SQLite data to Supabase.

### Environment

Create or update `.env` in the project root:

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL. Trailing slashes are trimmed. |
| `SUPABASE_SERVICE_ROLE_KEY` | Recommended | Service role key for trusted desktop sync writes. |
| `SUPABASE_KEY` | Fallback | Used only when the service role key is not set. |
| `SUPABASE_SCHEMA` | No | Supabase schema; defaults to `public`. |

### Symbols

| Symbol | Type | Description |
|---|---|---|
| `SYNC_MODELS` | `tuple[type]` | Ordered models synced to Supabase: `Exam`, `ExamSrtChunk`, `ExamContext`, `ExamQuestion`, `UserQuestionTag`, `ExamAttempt`, `UserAnswer`. |
| `TableSyncResult` | dataclass | Contains `table_name` and `row_count` for the UI summary. |
| `SupabaseSyncError` | exception | Raised when required Supabase settings are missing. |
| `sync_sqlite_to_supabase(batch_size=500)` | function | Reads all rows from local SQLite and upserts them into matching Supabase tables. |

### Behavior

Rows are serialized from SQLAlchemy column keys. `datetime.date` and
`datetime.datetime` values are converted to ISO strings; naive datetimes are
treated as UTC.

Supabase table names and columns must match the SQLAlchemy table names and
column keys. Rows are upserted by primary key `id`, so matching remote rows are
updated and missing rows are inserted. Upserts are sent in batches of
`batch_size`.

For non-`public` schemas, sync uses `client.schema(SUPABASE_SCHEMA)` before
selecting tables.

## Model Boundaries

- Models must not import PySide6.
- Views must not own database transaction logic.
- ViewModels should call `get_session()`, perform model operations, commit or
  rollback, and close sessions.
- Keep question grouping on `ExamContext`; keep question text/options/answers
  on `ExamQuestion`.
- Keep per-attempt aggregate counts on `ExamAttempt`, and recomputable
  per-question state on `UserAnswer`.
- Do not manually edit generated UI modules when changing model-backed views.
