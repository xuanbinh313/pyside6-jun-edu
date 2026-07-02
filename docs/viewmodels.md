# ViewModels Layer

> **Location:** `src/viewmodels/`  
> **Base class:** `PySide6.QtCore.QObject`  
> **Pattern:** All state-bearing ViewModels extend `QObject` and communicate with Views via Qt Signals.

---

## `ExamListViewModel`

**File:** [`src/viewmodels/exam_list_viewmodel.py`](../src/viewmodels/exam_list_viewmodel.py)

Manages the list of exams with real-time search filtering and deletion. It
receives an `IExamRepository` through constructor injection and defaults to
`SQLiteExamRepository`.

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

Manages a single exam's metadata and its SRT chunk list. Used by both **new exam creation** (no `exam_id`) and **editing** (existing `exam_id`). It receives an `IExamRepository` through constructor injection and stores pure dataclasses from `src.models.exam`.

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
| `save_exam()` | `(title, description, duration_minutes, is_published, audio_name) → None` | Upserts exam metadata; emits `data_saved` |
| `save_chunks()` | `→ None` | Replaces all DB chunks for this exam with `srt_chunks` (delete-all + re-insert) |
| `list_question_tags()` | `→ list[str]` | Returns tag names for the Groups & Questions filter. |
| `list_question_tags_for_context()` | `(context_id) → list[str]` | Returns tags assigned to a single exam context. |
| `set_context_tag()` | `(context_id, tag_name, enabled) → None` | Adds or removes one context tag through the repository. |
| `list_contexts()` | `(selected_tags=None) → list[ExamContext]` | Loads contexts through `IExamRepository`, optionally tag-filtered. |
| `list_questions_for_context()` | `(context_id) → list[ExamQuestion]` | Loads context questions through `IExamRepository`. |
| `context_question_numbers()` | `(context_id) → list[int]` | Returns ordered question numbers for context labels. |
| `delete_contexts_and_questions()` | `(context_ids, question_ids) → None` | Delegates context/question deletion to the repository. |
| `update_context_audio_segment()` | `(context_id, audio_start, audio_end) → ExamContext \| None` | Persists context audio metadata through the repository. |
| `import_contexts_and_questions()` | `(contexts_data, questions_data) → dict` | Imports parsed groups/questions through the repository. |
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
| `TTS_AGENT_URL` | `https://api.jun-edu.xyz` | Base URL of the TTS/alignment API service |

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

Runs SQLite/Supabase sync on a background thread and reports progress back to the main window.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `sync_started` | - | Sync worker starts |
| `sync_finished` | `list[TableSyncResult]` | All configured tables finish syncing |
| `sync_failed` | `str` | Sync raises an error |
| `local_sync_started` | - | Supabase-to-SQLite sync worker starts |
| `local_sync_finished` | `list[TableSyncResult]` | Remote rows and media finish syncing locally |
| `local_sync_failed` | `str` | Local sync raises an error |

### State

| Attribute | Type | Description |
|---|---|---|
| `is_syncing` | `bool` | Prevents overlapping sync runs |
| `_worker` | `SyncWorker \| None` | Active background thread |

### Methods

| Method | Description |
|---|---|
| `sync_to_supabase()` | Starts a `SyncWorker` unless sync is already running |
| `sync_to_local()` | Starts a Supabase-to-SQLite `SyncWorker` unless sync is already running |

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

## `ImportQuestionsViewModel`

**File:** [`src/viewmodels/import_questions_viewmodel.py`](../src/viewmodels/import_questions_viewmodel.py)

Owns the workflow state for `ImportQuestionsDialog`: prompt text variants, selected diagram image paths, question-number mapping, LLM JSON parsing/repair, answer-key CSV parsing, duplicate question-number validation, and final `result_contexts` / `result_questions` / `result_answer_key` payloads.

The dialog keeps Qt widget behavior only and delegates import parsing through `parse_import()`.

---

## `ImportQuestionsAgentViewModel`

**File:** [`src/viewmodels/import_questions_agent_viewmodel.py`](../src/viewmodels/import_questions_agent_viewmodel.py)

Coordinates the Gemini-backed PDF import workflow. It stores Part 1-7 PDF/page selections, editable prompts, answer-sheet image paths, persists each request as an SQLite import-agent task, and runs the agent call on `ImportQuestionsAgentWorker(QThread)`.

Selected PDF pages are sliced with `pypdf`, sent to Gemini through the `google-genai` SDK using `GEMINI_API_KEY`, parsed through `ImportQuestionsViewModel`, and exposed as `result_contexts`, `result_questions`, and `result_answer_key` for the existing exam import save path. Every part request requires an answer-sheet image: Parts 1-4 attach the listening answer sheet, and Parts 5-7 attach the reading/writing answer sheet so Gemini can set `correct_answer` during extraction. Each selected TOEIC part is sent as its own Gemini request, including Parts 1 and 2. Part 1 selected question pages are first converted locally into exactly two image crops per page with PyMuPDF plus OpenCV, but those image crops are local-only and are not uploaded to Gemini; only selected Part 1 transcript pages are sent for Part 1 extraction. Part 2 sends only its own selected transcript pages plus the dialog context text. Parsed Part 1 contexts are normalized to `IMAGE_DIAGRAM` with crop paths forced into `content._source_image_path`, `content.image_path`, and `content.image_filename`; if Gemini returns fewer Part 1 contexts than local crops, fallback image contexts/questions are appended so every crop is saved. Repository import then optimizes each crop to local WebP media and overwrites the saved context with the final local `image_path` and `image_filename`. Part 2 contexts are normalized to `STANDALONE` with `content.text` set from the dialog context input. Part 3 and Part 4 prompts instruct Gemini to use transcript range labels such as `41-43 refer to...` as the grouping boundary for shared `AUDIO_SRT` contexts. Agent prompts now prefer a top-level `contexts` array with each context carrying its nested `questions` array and append a Vietnamese note contract matching `ImportQuestionsViewModel`: context notes translate/summarize shared context text, question notes contain Vietnamese translations plus a separated Vietnamese explanation, and question notes must not be empty even when an answer key is unavailable. The `google-genai` request config sets `response_mime_type="application/json"` and `response_schema=ExamImportResponseSchema`, then `ImportQuestionsViewModel` flattens the parsed response into the existing database import contract before save.

Each send creates one `ImportAgentTask` row per selected TOEIC part. The ViewModel starts only one worker at a time, merges each successful result, then starts the next queued request. Any worker error marks the current row `failed`, stops the queue, and waits for the user to click Retry in the request status dialog before continuing.

---

## `SrtMappingAgentViewModel`

**File:** [`src/viewmodels/srt_mapping_agent_viewmodel.py`](../src/viewmodels/srt_mapping_agent_viewmodel.py)

Coordinates the Gemini-backed transcript alignment flow used by
`ExamTranscriptWidget`. It sends all current SRT chunks plus every exam context
and context question-number list to Gemini, asks for structured
`SrtMappingResponseSchema` JSON, saves the raw response under
`.codex/srt_mapping_responses/`, and emits mappings for the view to preview.

### Signals

| Signal | Payload | Emitted When |
|---|---|---|
| `mapping_ready` | `list[SrtChunkMapping]` | Gemini returns a valid mapping response |
| `progress_message` | `str` | Worker preparation, request, or response-save status changes |
| `error_message` | `str` | Validation, dependency, Gemini, or parsing fails |

### Methods

| Method | Description |
|---|---|
| `start_mapping(chunks, contexts, questions_by_context)` | Starts the background Gemini worker unless another mapping request is running. |
| `resolve_times(mappings, chunks)` | Converts returned chunk indexes into `(context_id, audio_start, audio_end)` tuples and silently skips invalid or unresolved mappings. |

The ViewModel owns the API/background work only. The preview table, confirmation
button, and final calls to `update_context_audio_segment()` stay in the view.

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
