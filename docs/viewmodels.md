# ViewModels Layer

> **Location:** `src/viewmodels/`  
> **Base class:** `PySide6.QtCore.QObject`  
> **Pattern:** All state-bearing ViewModels extend `QObject` and communicate with Views via Qt Signals.

---

## `ExamListViewModel`

**File:** [`src/viewmodels/exam_list_viewmodel.py`](../src/viewmodels/exam_list_viewmodel.py)

Manages the list of exams with real-time search filtering and deletion.

---

## `AuthViewModel`

**File:** [`src/viewmodels/auth_viewmodel.py`](../src/viewmodels/auth_viewmodel.py)

Manages optional login/register/logout state and saved-session restore. Supabase calls run on `AuthWorker(QThread)` so network I/O does not block the UI thread.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `state_changed` | - | Mode, status text, or loading state changes |
| `authenticated` | `str` email | Login or saved-session restore succeeds |
| `info_message` | `str` | Registration succeeds but email confirmation may be needed |
| `error_message` | `str` | Validation or Supabase auth fails |
| `logged_out` | - | Logout completes and local tokens are cleared |

### Methods

| Method | Description |
|---|---|
| `check_saved_session()` | Restores account state from local saved tokens without blocking access to the app |
| `login(email, password)` | Validates fields and signs in with Supabase |
| `register(email, password, confirm_password)` | Validates fields and creates a Supabase account |
| `sign_out()` | Signs out from Supabase and clears local tokens |

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `data_changed` | — | Exams list is reloaded (after load, search, or delete) |

### State

| Attribute | Type | Description |
|---|---|---|
| `exams` | `List[Exam]` | Currently loaded/filtered exam objects |
| `_search_query` | `str` | Active search string (case-insensitive LIKE filter) |

### Methods

| Method | Description |
|---|---|
| `load_exams()` | Queries DB, applies `_search_query` filter if set, emits `data_changed` |
| `set_search_query(query: str)` | Updates filter and calls `load_exams()` immediately |
| `delete_exam(exam_id: str)` | Deletes exam by ID, then reloads and emits `data_changed` |

---

## `ExamDetailsViewModel`

**File:** [`src/viewmodels/exam_details_viewmodel.py`](../src/viewmodels/exam_details_viewmodel.py)

Manages a single exam's metadata and its SRT chunk list. Used by both **new exam creation** (no `exam_id`) and **editing** (existing `exam_id`).

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `data_loaded` | — | `load_exam()` completes |
| `data_saved` | — | `save_exam()` commits successfully |

### State

| Attribute | Type | Description |
|---|---|---|
| `exam_id` | `str \| None` | UUID of the exam being edited; `None` for new exams |
| `exam` | `Exam \| None` | Loaded exam ORM object (detached from session) |
| `srt_chunks` | `List[ExamSrtChunk]` | In-memory list of chunks for editing |

### Methods

| Method | Signature | Description |
|---|---|---|
| `load_exam()` | `→ None` | Loads exam + chunks from DB; expunges from session; emits `data_loaded` |
| `save_exam()` | `(title, description, duration_minutes, is_published) → None` | Upserts exam metadata; emits `data_saved` |
| `save_chunks()` | `→ None` | Replaces all DB chunks for this exam with `srt_chunks` (delete-all + re-insert) |
| `duplicate_chunk()` | `(chunk) → (new_idx, new_chunk)` | Inserts a copy of `chunk` after it in `srt_chunks`; assigns next max index |
| `merge_chunk()` | `(chunk) → (idx, removed_chunk) \| (None, None)` | Merges text + end_time of chunk with the next chunk; removes next chunk |

> **Note:** `save_chunks()` is a destructive full-replace — all existing DB chunks are deleted then re-inserted.

---

## `ExamTakeViewModel`

**File:** [`src/viewmodels/exam_take_viewmodel.py`](../src/viewmodels/exam_take_viewmodel.py)

Manages the learner-facing exam flow: exam summary, previous attempts, practice filters, real-test sessions, shuffled option mapping, grading, and atomic result persistence.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `data_loaded` | — | Exam metadata, questions, tags, and history are loaded |
| `test_started` | — | A practice or real-test session is generated |
| `result_ready` | — | Attempt and per-question answers are saved |
| `error_message` | `str` | Load, filter, or persistence errors occur |

### State

| Attribute | Type | Description |
|---|---|---|
| `exam` | `Exam \| None` | Loaded exam metadata |
| `contexts` | `List[ExamContext]` | Exam contexts ordered by part/index |
| `questions` | `List[ExamQuestion]` | Exam questions ordered by question number |
| `attempts` | `List[AttemptSummary]` | Previous attempts |
| `active_questions` | `List[QuestionSession]` | Current test questions with shuffled option mapping |

### Answer Mapping

`QuestionSession.options` stores both shuffled display information and canonical option letters. Views submit a shuffled `display_index`; the ViewModel converts that to the canonical `A`-`D` letter and stores only the canonical letter in `user_answers.user_choice`.

### Persistence

`complete_test()` creates one `ExamAttempt` plus one `UserAnswer` per active question in a single SQLAlchemy transaction. Unanswered questions are stored with `user_choice=None` and `is_correct=False`.

### Attempt Analytics

`load_attempt_analytics(attempt_id)` joins `exam_attempts`, `user_answers`, `exam_questions`, and `exam_contexts` to produce KPI totals, part-specific category breakdowns, an overall category breakdown, and per-question answer details. `start_review_questions(question_ids)` starts a filtered practice session for retaking incorrect or skipped answers.

---

## `ExamAddExternalViewModel`

**File:** [`src/viewmodels/exam_add_external_viewmodel.py`](../src/viewmodels/exam_add_external_viewmodel.py)

Handles the two-phase async workflow for importing an exam from an external audio file:

1. **Phase 1 — Analyze:** Upload audio → extract transcript text via `POST /api/extract-text`
2. **Phase 2 — Align:** Submit corrected text → align audio segments via `POST /api/align-audio` → save to DB

All HTTP calls run on a background `QThread` via the internal `Worker` class.

### Environment

| Variable | Default | Description |
|---|---|---|
| `TTS_AGENT_URL` | `https://api.jun-edu.shop` | Base URL of the TTS/alignment API service |

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `state_changed` | — | Any state change (loading start/end, file set, reset) |
| `progress_message` | `str` | Background worker progress update text |
| `error_message` | `str` | Error occurred in background task |
| `exam_saved` | `str` (exam_id) | Exam successfully created in DB after alignment |

### State

| Attribute | Type | Description |
|---|---|---|
| `audio_file_path` | `str \| None` | Absolute path of selected audio file |
| `audio_file_name` | `str \| None` | Basename of audio file |
| `text` | `str` | Extracted/edited transcript text |
| `is_loading` | `bool` | True while background worker is running |
| `is_analyzed` | `bool` | True after Phase 1 succeeds |
| `current_task_id` | `str \| None` | Server-side task ID for polling |

### Methods

| Method | Description |
|---|---|
| `set_audio_file(path)` | Sets audio path, resets analysis state, emits `state_changed` |
| `set_text(text)` | Updates `self.text` (called on every text edit) |
| `analyze()` | Starts Phase 1 worker; emits `state_changed` |
| `add_or_update()` | Starts Phase 2 worker; emits `state_changed` |
| `reset()` | Clears all state back to initial; emits `state_changed` |
| `poll_task_status(task_id, emit_progress)` | Polls `GET /api/check-status/{task_id}` every 2 s until `completed` or `failed` |

### Worker

`Worker(QThread)` is a generic background task runner:
```python
Worker(func, *args, **kwargs)
# func signature: func(emit_progress, *args, **kwargs) -> dict
```
Emits `progress(str)`, `finished(dict)`, or `error(str)`.

### API Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/extract-text` | `POST` | Upload audio, get `task_id` |
| `/api/check-status/{task_id}` | `GET` | Poll for task completion |
| `/api/align-audio` | `POST` | Submit `task_id` + corrected text for alignment |

---

## `SyncViewModel`

**File:** [`src/viewmodels/sync_viewmodel.py`](../src/viewmodels/sync_viewmodel.py)

Runs SQLite-to-Supabase sync on a background thread and reports progress back to the main window.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `sync_started` | - | Sync worker starts |
| `sync_finished` | `list[TableSyncResult]` | All configured tables finish syncing |
| `sync_failed` | `str` | Sync raises an error |

### State

| Attribute | Type | Description |
|---|---|---|
| `is_syncing` | `bool` | Prevents overlapping sync runs |
| `_worker` | `SyncWorker \| None` | Active background thread |

### Methods

| Method | Description |
|---|---|
| `sync_to_supabase()` | Starts a `SyncWorker` unless sync is already running |

---

## `ExamTranscriptViewModel`

**File:** [`src/viewmodels/exam_transcript_viewmodel.py`](../src/viewmodels/exam_transcript_viewmodel.py)

A lightweight ViewModel (no `QObject`, no Signals) used directly by `ExamTranscriptWidget` for in-memory chunk manipulation.

### State

| Attribute | Type | Description |
|---|---|---|
| `exam` | `Exam \| None` | Reference to the exam |
| `srt_chunks` | `List[ExamSrtChunk]` | Current chunk list |

### Methods

| Method | Signature | Description |
|---|---|---|
| `load_chunks(chunks)` | `(List[ExamSrtChunk]) → None` | Replaces `srt_chunks` with the provided list |
| `duplicate_chunk(chunk)` | `→ (new_idx, new_chunk)` | Same logic as `ExamDetailsViewModel.duplicate_chunk` |
| `merge_chunk(chunk)` | `→ (idx, removed) \| (None, None)` | Same logic as `ExamDetailsViewModel.merge_chunk` |
| `save_chunks()` | `→ None` | Persists to DB (delete-all + re-insert for this exam) |

> **Note:** This ViewModel duplicates chunk logic from `ExamDetailsViewModel`. Future refactor opportunity.

---

## `ReminderViewModel`

**File:** [`src/viewmodels/reminder_viewmodel.py`](../src/viewmodels/reminder_viewmodel.py)

Manages a single countdown timer that fires a study reminder when it expires.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `show_study_window` | — | Timer reaches zero |
| `tick_tock` | `int` (remaining seconds) | Every timer tick (1 s) |

### State

| Attribute | Type | Description |
|---|---|---|
| `timer` | `QTimer` | Internal 1-second interval timer |
| `time_left_seconds` | `int` | Remaining seconds until reminder fires |

### Methods

| Method | Signature | Description |
|---|---|---|
| `start_countdown(minutes)` | `(int) → None` | Starts timer if not already running. Guards against double-start. |

### Timer Flow

```
start_countdown(N)
  → time_left_seconds = N * 60
  → QTimer.start(1000)
      → _on_timer_timeout() every second
          → tick_tock.emit(remaining)
          → if remaining <= 0:
              timer.stop()
              show_study_window.emit()
```
