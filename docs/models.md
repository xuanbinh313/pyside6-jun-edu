# Models And Repositories

> **Pure models:** `src/models/`  
> **Repository interfaces:** `src/repositories/base_repo.py`  
> **SQLite implementation:** `src/repositories/sqlite/`  
> **Supabase implementation:** `src/repositories/supabase/`

The project is migrating to a strict multi-DB MVVM shape. Data that crosses
repository, ViewModel, and View boundaries must be represented as pure Python
dataclasses from `src/models/`. Database-specific objects stay inside concrete
repository implementations.

## `src/models/exam.py`

This module contains framework-agnostic domain dataclasses plus Pydantic schemas
for external agent response contracts:

| Class | Purpose |
|---|---|
| `Exam` | Top-level exam metadata plus optional child lists. |
| `ExamSrtChunk` | Transcript/audio segment data. |
| `ExamContext` | Shared context for one or more questions, including context-level `additional_meta`. |
| `ExamQuestion` | Question stem, options, answer, and question-level note metadata. |
| `UserQuestionTag` | Per-user tag assigned to a question. |
| `ExamAttempt` | Completed learner attempt summary. |
| `UserAnswer` | Per-question answer for an attempt. |
| `ImportAgentTask` | Persisted Gemini import-agent request payload, status, attempts, error, and result for retry tracking. |
| `ExamImportResponseSchema` | Pydantic response schema used by `google-genai` for agent-import JSON. |
| `ExamImportContextSchema` | Pydantic context schema containing nested imported questions. |
| `ExamImportQuestionSchema` | Pydantic imported-question schema used inside each imported context. |

`AdditionalMeta` stores context-level audio timing:

| Key | Type |
|---|---|
| `audio_start` | `float` |
| `audio_end` | `float` |
| `note` | `str` |

`QuestionAdditionalMeta` stores only question-level note text:

| Key | Type |
|---|---|
| `note` | `str` |

`src/models/exam.py` must not import SQLAlchemy or PySide6. Pydantic schemas in
this file are API contracts only; repositories still map database rows to the
domain dataclasses above before returning data to ViewModels.

## Repository Interfaces

`src/repositories/base_repo.py` defines abstract repository contracts. ViewModels
depend on these interfaces and should receive a repository instance through
constructor injection.

`IExamRepository` currently covers the migrated exam list/details/transcript
workflow:

| Method | Description |
|---|---|
| `list_exams(search_query)` | Returns pure `Exam` dataclasses. |
| `delete_exam(exam_id)` | Deletes an exam by ID. |
| `get_exam_details(exam_id)` | Returns pure exam, transcript chunks, contexts, and questions. |
| `save_exam(...)` | Creates or updates exam metadata and returns the exam ID. |
| `replace_srt_chunks(exam_id, chunks)` | Replaces persisted transcript chunks for an exam. |
| `list_question_tags()` | Returns distinct question tag names for filters. |
| `list_question_tags_for_question(question_id)` | Returns ordered tag names assigned to one question. |
| `set_question_tag(question_id, tag_name, enabled)` | Adds or removes one question tag and marks new tags dirty for sync. |
| `list_contexts(exam_id, selected_tags)` | Returns contexts for the groups/questions view, optionally filtered by tags. |
| `list_questions_for_context(context_id)` | Returns pure question dataclasses for one context. |
| `get_context_question_numbers(context_id)` | Returns ordered question numbers for context labels. |
| `delete_contexts_and_questions(context_ids, question_ids)` | Deletes selected context/question records in a repository transaction. |
| `update_context_audio_segment(context_id, audio_start, audio_end)` | Updates context audio timing metadata and returns the updated context. |
| `import_contexts_and_questions(exam_id, contexts_data, questions_data)` | Imports parsed question groups, tracks diagram media locally, and returns import counts. |

## SQLite Repository

`src/repositories/sqlite/database.py` owns the SQLAlchemy engine, base, session
factory, and schema initialization.

`src/repositories/sqlite/orm_models.py` owns all SQLAlchemy `Mapped`,
`mapped_column`, `relationship`, and table declarations.

`src/repositories/sqlite/sqlite_repo.py` maps ORM rows to pure dataclasses before
returning data to ViewModels. Repository methods open, commit/rollback, and close
their own sessions.

`src/repositories/sqlite/import_agent_task_repo.py` owns persisted Gemini
agent-import request tasks. It stores the request payload before the worker
starts, updates `queued` / `running` / `succeeded` / `failed` status, tracks
attempt counts, schedules retryable busy-service failures, and deletes
non-running tasks when requested from the status dialog.

## Supabase Repository

`src/repositories/supabase/client.py` owns Supabase client construction,
`src/repositories/supabase/auth.py` owns login/session helpers, and
`src/repositories/supabase/sync.py` owns bidirectional SQLite/Supabase sync.

Media attachments are tracked locally in the SQLite `mediafiles` table. Imported
audio and diagram files are saved under the app's local media folder with
validated lowercase filenames, marked `dirty=True`, and uploaded to Cloudflare R2
during SQLite-to-Supabase sync before their `mediafiles` row is upserted. Exams
store audio by `audio_name` only; views resolve that filename back to the local
media folder for playback.

Supabase-to-SQLite sync downloads the signed-in user's remote rows into local
SQLite and downloads each `mediafiles` object from R2 key
`media/{user_id}/{filename}` into the same temp media folder. Downloaded media
rows are marked `dirty=False` locally; exam audio continues to reference the
downloaded file by `audio_name`.

R2 sync reads these `.env` settings:

| Variable | Description |
|---|---|
| `CLOUDFLARE_R2_ENDPOINT` | R2 S3-compatible endpoint, with or without `https://` |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | R2 access key |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | R2 secret key |
| `CLOUDFLARE_R2_BUCKET` | Target bucket |

`src/repositories/supabase/supabase_repo.py` is the placeholder for stateless
Supabase API-backed repositories. It should map JSON dictionaries into
`src.models` dataclasses before returning data to ViewModels.

## Migration Notes

The first migrated ViewModels are:

| ViewModel | Repository Use |
|---|---|
| `ExamListViewModel` | Loads/searches/deletes exams through `IExamRepository`. |
| `ExamDetailsViewModel` | Loads/saves exam metadata and transcript chunks through `IExamRepository`. |
| `ExamTranscriptViewModel` | Persists transcript chunk replacement through `IExamRepository`. |

Some legacy views and larger ViewModels still call SQLite infrastructure
directly during the incremental migration. Those calls now import from
`src.repositories.sqlite.*`, keeping SQLAlchemy out of `src/models/` while the
remaining UI workflows are moved behind repository methods.
