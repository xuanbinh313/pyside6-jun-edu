# Views Layer

> **Location:** `src/views/`  
> **Pattern:** Views receive a ViewModel reference at construction time. They connect to ViewModel signals in `__init__` and never directly touch the database.
> **Generated UI:** Views import `Ui_*` classes from `ui_gen/`. Do not edit generated files by hand; edit `ui/*.ui` and regenerate with `pyside6-uic`.

---

## `ExamListView`

**File:** [`src/views/exam_list_view.py`](../src/views/exam_list_view.py)  
**ViewModel:** `ExamListViewModel`

The home screen. Displays all exams in a table with search, add, learner start, and per-row edit/delete actions.

---

## `AuthView`

**File:** [`src/views/auth_view.py`](../src/views/auth_view.py)  
**ViewModel:** `AuthViewModel`

Login/register modal opened from the main menu. It uses [`ui/auth_view.ui`](../ui/auth_view.ui) and [`ui_gen/ui_auth_view.py`](../ui_gen/ui_auth_view.py). The main exam views remain accessible without signing in.

### UI Elements

| Widget | ID | Description |
|---|---|---|
| `QLineEdit` | `email_input` | Email input with clear button |
| `QLineEdit` | `password_input` | Masked password input |
| `QLineEdit` | `confirm_password_input` | Masked confirmation input, visible only in register mode |
| `QPushButton` | `primary_button` | Login or Register action |
| `QPushButton` | `toggle_button` | Switches between login and register modes |
| `QProgressBar` | `loading_bar` | Indeterminate loading indicator during Supabase calls |
| `QLabel` | `message_label` | Inline validation or status text |

### Constructor

```python
ExamListView(viewmodel: ExamListViewModel, navigate_to_details_callback: Callable[[str | None], None])
```

### Signal Connections

| ViewModel Signal | View Slot | Effect |
|---|---|---|
| `data_changed` | `on_data_changed()` | Rebuilds table rows from `viewmodel.exams` |

### UI Elements

| Widget | ID | Description |
|---|---|---|
| `QLabel` | title | "Exam List" header (blue, bold) |
| `QLineEdit` | `search_input` | Live search — calls `viewmodel.set_search_query()` on `textChanged` |
| `QPushButton` | "Add Exam" | Navigates to details with `None` (new exam) |
| `QPushButton` | "Add External" | Navigates to details with `"EXTERNAL"` |
| `QTableWidget` | `table` | 5 columns: Title, Duration, Published, Start, Manage |

### Table Actions (per row)

- **Start** — `navigate_to_take(exam.id)`
- **Edit** — `navigate_to_details(exam.id)`
- **Delete** — `viewmodel.delete_exam(exam.id)`

---

## `ExamDetailsView`

**File:** [`src/views/exam_details_view.py`](../src/views/exam_details_view.py)  
**ViewModel:** `ExamDetailsViewModel`

A tabbed detail screen for a single exam. Hosts three sub-widgets as tabs.

### Constructor

```python
ExamDetailsView(viewmodel: ExamDetailsViewModel, go_back_callback: Callable[[], None])
```

Immediately calls `viewmodel.load_exam()` on construction.

### Signal Connections

| ViewModel Signal | View Slot | Effect |
|---|---|---|
| `data_loaded` | `on_data_loaded()` | Populates `form_tab` and `transcript_tab` |

### Tabs

| Tab Label | Widget | Description |
|---|---|---|
| "Exam Details" | `ExamFormWidget` | Metadata form (title, description, audio, duration, published) |
| "Groups & Questions" | `ExamGroupsWidget` | Full question list with tag filtering, answer checking, and audio segment playback |
| "Transcript" | `ExamTranscriptWidget` | SRT chunk editor with audio player |

---

## `ExamTakeView`

**File:** [`src/views/exam_take_view.py`](../src/views/exam_take_view.py)  
**ViewModel:** `ExamTakeViewModel`

Learner-facing exam screen reached from the exam list Start action. It uses [`ui/exam_take_view.ui`](../ui/exam_take_view.ui) and [`ui_gen/ui_exam_take_view.py`](../ui_gen/ui_exam_take_view.py) for the shell, then builds overview, test, and result pages dynamically.

### Constructor

```python
ExamTakeView(viewmodel: ExamTakeViewModel, go_back_callback: Callable[[], None])
```

### Signal Connections

| ViewModel Signal | View Slot | Effect |
|---|---|---|
| `data_loaded` | `_render_overview()` | Shows exam metadata, history table, and mode tabs |
| `test_started` | `_render_test()` | Renders shuffled question cards |
| `result_ready` | `_render_result()` | Shows score and per-question canonical answer breakdown |
| `error_message` | `_show_error(msg)` | Shows a warning dialog |

### Pages

| Page | Description |
|---|---|
| Overview | Title, description, duration, part count, question count, previous attempts, Practice and Real Test tabs |
| Test | Scrollable question cards with shuffled options; Practice mode includes per-question Skip |
| Result | Score/total plus per-question question text, user's canonical letter, correct canonical letter, and correct text |
| Attempt Analytics | KPI cards, part/overall category breakdowns, answer-sheet tiles, question detail dialogs, and Retake Wrong Answers |

The View submits only the selected shuffled display index. `ExamTakeViewModel` maps it back to the canonical `A`-`D` answer before grading and persistence.

The previous-attempts table View action navigates to the Attempt Analytics page. Badge buttons and answer-sheet Details buttons open a modal with the context, question, user choice, and correct answer. Retake Wrong Answers starts a filtered practice session containing the attempt's incorrect or skipped questions.

---

## `ExamAddExternalView`

**File:** [`src/views/exam_add_external_view.py`](../src/views/exam_add_external_view.py)  
**ViewModel:** `ExamAddExternalViewModel`

Screen for importing an exam from an external audio file via the TTS API.

### Constructor

```python
ExamAddExternalView(
    viewmodel: ExamAddExternalViewModel,
    go_back_callback: Callable[[], None],
    navigate_to_details_callback: Callable[[str], None]
)
```

### Signal Connections

| ViewModel Signal | View Slot | Effect |
|---|---|---|
| `state_changed` | `update_ui()` | Updates button text/state, file label, text area |
| `progress_message` | `show_progress(msg)` | Updates `progress_label` text |
| `error_message` | `show_error(msg)` | Shows `QMessageBox.critical` |
| `exam_saved` | `on_exam_saved(exam_id)` | Shows success dialog, navigates to exam details |

### UI Elements

| Widget | ID | Description |
|---|---|---|
| `QPushButton` | "← Back" | Returns to list |
| `QPushButton` | `reset_btn` | Calls `viewmodel.reset()` |
| `QLabel` | `file_label` | Shows selected file name or "No audio selected" |
| `QPushButton` | `pick_btn` | Opens file dialog for `.mp3`/`.wav` |
| `QTextEdit` | `text_edit` | Displays extracted text; user can edit before alignment |
| `QPushButton` | `action_btn` | "Analyze" → "Add or Update Exam" based on `is_analyzed` state |
| `QLabel` | `progress_label` | Shows background task status messages |

### State-Driven UI Logic (`update_ui`)

```
is_loading=True   → action_btn disabled, text = "Loading..."
is_analyzed=False → action_btn text = "Analyze"
is_analyzed=True  → action_btn text = "Add or Update Exam"
current_task_id set → pick_btn disabled (audio locked)
```

---

## Component Widgets

### `ExamFormWidget`

**File:** [`src/views/components/exam_form_widget.py`](../src/views/components/exam_form_widget.py)

Form for editing exam metadata. Used as a tab inside `ExamDetailsView`.

#### Extracted Helpers

| File | Responsibility |
|---|---|
| [`src/views/components/exam_context_section.py`](../src/views/components/exam_context_section.py) | Reusable context block with title, audio controls, edit action, rendered rich-text body, and note display |
| [`src/views/components/exam_context_html.py`](../src/views/components/exam_context_html.py) | Pure rendering helpers for `READING_PASSAGE`, `AUDIO_SRT`, and `IMAGE_DIAGRAM` context content |

#### Key Methods

| Method | Description |
|---|---|
| `populate()` | Fills all fields from `viewmodel.exam` |
| `on_upload_audio()` | File dialog → sets `audio_input` text (local path) |
| `on_attach_srt()` | Opens `.srt` file dialog → calls `parse_srt()` |
| `on_import_csv()` | Opens `.csv` file dialog, parses rows as `ExamSrtChunk` objects |
| `on_save()` | Copies/downloads `audio_input` into local media, saves the resulting `audio_name`, then calls `viewmodel.save_exam()` |
| `parse_srt(file_path)` | Parses standard SRT format into `ExamSrtChunk` list, writes to `viewmodel.srt_chunks` |

#### SRT Parser

Handles standard SRT format:
```
1
00:00:01,000 --> 00:00:03,000
Text content here
```
- Multi-line text blocks are joined with spaces
- Timestamps converted from `HH:MM:SS,mmm` to float seconds

#### CSV Import Format

Expected header row + data rows: `index,start,end,text[,...]`  
(Extra commas in text are preserved via `",".join(parts[3:])`)

---

### `ExamGroupsWidget`

**File:** [`src/views/components/exam_groups_widget.py`](../src/views/components/exam_groups_widget.py)

Full Groups & Questions panel. Layout loaded from [`ui/exam_groups_widget.ui`](../ui/exam_groups_widget.ui) via `pyside6-uic` and generated into [`ui_gen/ui_exam_groups_widget.py`](../ui_gen/ui_exam_groups_widget.py).

In `setup_ui()`:

```python
self.ui = Ui_ExamGroupsWidget()
self.ui.setupUi(self)
```

Named widgets from `.ui` file:

| Widget Name | Type | Description |
|---|---|---|
| `q_label` | `QLabel` | "Exam Questions" section header |
| `import_q_btn` | `QPushButton` | Import questions from CSV (28×28 icon button) |
| `filter_label` | `QLabel` | "Filter by Tags:" label |
| `tag_filter_list` | `QListWidget` | Checkable tag filter list (max height 80px) |
| `q_list` | `QListWidget` | Active-part context and question list (supports ExtendedSelection + right-click context menu on contexts) |
| `title_label` | `QLabel` | Hidden at runtime and replaced by part tabs for right-panel navigation |
| `listen_widget` | `QWidget` | Audio listen controls — hidden until a question with audio is selected |
| `listen_btn` | `QPushButton` | Play button for the question's audio segment |
| `status_label` | `QLabel` | Shows current audio segment timestamps |
| `passage_label` | `QLabel` | "Reading Passage" label — hidden for non-reading questions |
| `passage_browser` | `QTextBrowser` | Passage text display (yellow background) |
| `transcript_label` | `QLabel` | "Transcript Context" label — hidden until audio segment is set |
| `transcript_browser` | `QTextBrowser` | SRT chunk transcript for the selected audio segment |
| `options_scroll` | `QScrollArea` | Scrollable container for the active part's context sections and question option radio buttons |
| `options_container` | `QWidget` | Inner widget of `options_scroll` |
| `options_layout` | `QVBoxLayout` | Layout that holds `OptionWidget` instances |

#### Helper Classes

- **`TagMenuDialog`** — floating popup dialog (`QDialog` with `Popup | FramelessWindowHint`) for adding/removing tags on an exam context.
- **`SelectTranscriptDialog`** — dialog to select one or more SRT chunks to set the audio segment timestamps on a question.
- **`EditQuestionDialog`** — form dialog to edit question fields: Part, Correct Answer, Content, and Options A–D.
- **`EditContextDialog`** — inline editor dialog for editing `ExamContext` text content.
- **`OptionWidget`** — renders ABCD radio buttons for a single question in the saved option order. The correct answer is validated by original DB index.

#### Key Methods

| Method | Description |
|---|---|
| `populate()` | Loads audio source, populates `q_list`, resets right panel |
| `_populate_q_list(questions)` | Fills `q_list` with context-section headers followed by their respective questions |
| `populate_tags()` | Fills `tag_filter_list` with all distinct user tags |
| `_on_question_selected(current, previous)` | Shows question detail, audio controls, passage/transcript, and manages context edit controls |
| `_on_filter_changed()` | Filters `q_list` based on selected tags |
| `_on_listen_clicked()` | Seeks and plays the audio segment for the selected question |
| `_on_import_questions_clicked()` | Opens `ImportQuestionsDialog` |
| `_on_import_questions_agent_clicked()` | Opens `ImportQuestionsAgentDialog` for Gemini PDF/page import |
| `_on_q_list_context_menu(pos)` | Right-click menu with Edit / Delete / Duplicate actions (filters actions based on item type) |
| `_on_edit_context()` | Opens `EditContextDialog` to modify the currently selected context |
| `_refresh_ctx_header_item(ctx)` | Refreshes the display text of a context header in the question list |
| `on_question_edited(updated_q)` | Called by `OptionWidget` after an inline question edit to refresh the list item text |
| `on_question_tag_changed()` | Called by `TagMenuPopup` to refresh the tag filter list |
| `on_question_audio_changed(question)` | Called by `OptionWidget` after saving a new audio segment |

#### Add/Edit Question Dialog

`AddExamQuestionDialog` owns Qt widget state for one context and its questions. Defaults, validation, image normalization, and context/question persistence are delegated to `AddExamQuestionViewModel`.

#### Import Questions Dialog

`ImportQuestionsDialog` supports structured JSON import plus an optional answer-key CSV lane. The answer-key prompt asks the LLM to return only:

```csv
question,answer
1,A
2,B
```

When CSV answers are pasted, the dialog applies them to newly imported question data before saving. `ExamGroupsWidget` also sends the answer map through the ViewModel so existing `ExamQuestion.correct_answer` values in the current exam are updated by `question_number`; missing question numbers are ignored.

Parsing, selected image state, duplicate validation, and final import payloads are owned by `ImportQuestionsViewModel`; the dialog handles prompt editing, file picking, messages, and accept/reject flow.

#### Import Questions Agent Dialog

`ImportQuestionsAgentDialog` adds a visual PDF/page workflow for TOEIC Parts 1-7. The dialog is split into Listening and Reading tabs: Listening contains Parts 1-4 with its own answer-sheet drop area and overall PDF source panel, while Reading contains Parts 5-7 with its own reading/writing answer sheet and source panel. Each tab scrolls as one page containing the answer sheet, source PDF panel, and part step panels. Selected source pages are extracted to section-specific temp files such as `temp_listening_questions_pdf.pdf`, `temp_listening_transcripts_pdf.pdf`, `temp_reading_questions_pdf.pdf`, and `temp_reading_transcripts_pdf.pdf` before part-level selection begins. Each step opens the generated temp question/transcript PDF in the page selector, and the selector only assigns pages to parts in the active tab; Part 2 keeps a context text input defaulting to "Mark your answer on your answer sheet" instead of question-page selection. Prompts are edited from each step through a dedicated prompt dialog. Parts 1-4 require the listening answer sheet, and Parts 5-7 require the reading/writing answer sheet before sending. Part 1 question pages are split into two image crops per selected page before upload and saved as `IMAGE_DIAGRAM` contexts. Parts 5-7 use the reading prompt contract from `ImportQuestionsViewModel.READING_PROMPT_TEXT`. The dialog includes a Requests button that stays available during loading and opens an agent-request status table with queued/running/succeeded/failed state, attempts, errors, manual retry, refresh, and removal for non-running requests. The agent dialog delegates Gemini calls, PDF slicing, image splitting, answer-sheet attachment, sequential SQLite task tracking, retry, and response parsing to `ImportQuestionsAgentViewModel`, then returns the same import payload contract used by the manual dialog.

---

### `ExamTranscriptWidget`

**File:** [`src/views/components/exam_transcript_widget.py`](../src/views/components/exam_transcript_widget.py)

The most complex component. A full-featured audio player and SRT chunk editor.

#### Sub-widget: `TimeAdjustWidget`

Inline `±0.1s` spinner for precise timestamp editing.

```
[ − ] [ 0.000 ] [ + ]
```

- Editable text field + increment/decrement buttons (0.1 s step)
- Calls `on_change(float)` callback when value changes
- Uses `qtawesome` icons: `fa5s.minus` (red), `fa5s.plus` (blue)

#### UI Loading

Layout loaded from [`ui/exam_transcript_widget.ui`](../ui/exam_transcript_widget.ui) via `pyside6-uic` and generated into [`ui_gen/ui_exam_transcript_widget.py`](../ui_gen/ui_exam_transcript_widget.py).

In `setup_ui()`:

```python
self.ui = Ui_ExamTranscriptWidget()
self.ui.setupUi(self)
```

Named widgets from `.ui` file:

| Widget Name | Type | Description |
|---|---|---|
| `play_pause_btn` | `QPushButton` | Global play/pause toggle |
| `delay_spin` | `QSpinBox` | Loop delay in seconds before next loop iteration |
| `auto_detect_audio_btn` | `QPushButton` | Runtime-added button that asks Gemini to map SRT chunks to context audio windows |
| `add_to_question_btn` | `QPushButton` | Saves the selected transcript row span to a selected exam context; enabled only when rows are selected |
| `save_btn` | `QPushButton` | Save changes — only visible when `_has_changes` is `True` |
| `table` | `QTableWidget` | 5-column SRT chunk table with extended row selection |
| `seek_slider` | `QSlider` | Audio seek bar (horizontal) |
| `time_current_label` | `QLabel` | Current position (seconds, 3 decimal places) |
| `time_total_label` | `QLabel` | Total duration (seconds, 3 decimal places) |

#### Table Columns

| # | Content | Editable |
|---|---|---|
| 0 | Chunk index | No (read-only) |
| 1 | Start time | `TimeAdjustWidget` |
| 2 | End time | `TimeAdjustWidget` |
| 3 | Text | Yes (inline edit) |
| 4 | Actions | Buttons (play, loop, duplicate, merge) |

#### Row Actions

| Icon | Color | Tooltip | Action |
|---|---|---|---|
| `fa5s.play` | Green | Play Once | `play_range(start, end)` — plays chunk once |
| `fa5s.sync-alt` | Blue | Loop | `_toggle_loop(chunk)` — loops chunk with delay |
| `fa5s.copy` | Amber | Duplicate | `_duplicate_chunk(chunk)` → `viewmodel.duplicate_chunk()` |
| `fa5s.compress-arrows-alt` | Grey | Merge Next | `_merge_chunk(chunk)` → `viewmodel.merge_chunk()` |

#### Audio Player

- Backend: `QMediaPlayer` + `QAudioOutput`
- Supports local file paths and HTTP URLs
- Seek slider updates position; dragging blocks signal feedback loop
- Position tracking auto-highlights the matching table row during playback

#### Loop Mechanic

```
_toggle_loop(chunk)
  → play_range(start, end, loop_idx=chunk.index)
      → play_until = end_time_ms
      → on positionChanged: if pos >= play_until:
          pause()
          QTimer.singleShot(delay_ms, _play_loop)
              → _play_loop(loop_idx)  [repeat]
```

Toggling loop on the same chunk cancels it (`looping_chunk_idx = None`).

#### Change Tracking

`_has_changes` flag is set by `_mark_changed()` whenever text or timestamps are edited. The `save_btn` becomes visible on first change and hidden after save.

#### Key Methods

| Method | Description |
|---|---|
| `populate()` | Loads audio source, clears table, inserts all chunk rows |
| `play_range(start, end, loop_idx)` | Seeks and plays; optionally loops |
| `_toggle_play()` | Play ↔ Pause |
| `_update_play_pause_icon()` | Swaps icon/text based on `playbackState` |
| `_on_save_clicked()` | Calls `viewmodel.save_chunks()`, clears change flag |
| `_on_auto_detect_audio_clicked()` | Sends all chunks, contexts, and context question numbers to `SrtMappingAgentViewModel`; opens a preview table before saving detected audio windows |
| `_on_add_to_question_clicked()` | Opens an exam context picker and saves `audio_start` from the first selected row and `audio_end` from the last selected row |
| `_on_item_changed(item)` | Syncs text column edits back to the chunk object |
| `_duplicate_chunk(chunk)` | Delegates to ViewModel, inserts new row at correct position |
| `_merge_chunk(chunk)` | Delegates to ViewModel, updates text/end in place, removes next row |
