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

This module contains framework-agnostic dataclasses:

| Class | Purpose |
|---|---|
| `Exam` | Top-level exam metadata plus optional child lists. |
| `ExamSrtChunk` | Transcript/audio segment data. |
| `ExamContext` | Shared context for one or more questions, including context-level `additional_meta`. |
| `ExamQuestion` | Question stem, options, answer, and question-level note metadata. |
| `UserQuestionTag` | Per-user tag assigned to a question. |
| `ExamAttempt` | Completed learner attempt summary. |
| `UserAnswer` | Per-question answer for an attempt. |

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

`src/models/exam.py` must not import SQLAlchemy or PySide6.

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

## SQLite Repository

`src/repositories/sqlite/database.py` owns the SQLAlchemy engine, base, session
factory, and schema initialization.

`src/repositories/sqlite/orm_models.py` owns all SQLAlchemy `Mapped`,
`mapped_column`, `relationship`, and table declarations.

`src/repositories/sqlite/sqlite_repo.py` maps ORM rows to pure dataclasses before
returning data to ViewModels. Repository methods open, commit/rollback, and close
their own sessions.

## Supabase Repository

`src/repositories/supabase/client.py` owns Supabase client construction,
`src/repositories/supabase/auth.py` owns login/session helpers, and
`src/repositories/supabase/sync.py` owns SQLite-to-Supabase sync.

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
