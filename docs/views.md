# Views Layer

> **Location:** `src/views/`  
> **Pattern:** Views receive a ViewModel reference at construction time. They connect to ViewModel signals in `__init__` and never directly touch the database.

---

## `ExamListView`

**File:** [`src/views/exam_list_view.py`](../src/views/exam_list_view.py)  
**ViewModel:** `ExamListViewModel`

The home screen. Displays all exams in a table with search, add, and per-row edit/delete actions.

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
| `QTableWidget` | `table` | 4 columns: Title, Duration, Published, Actions |

### Table Actions (per row)

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

#### Key Methods

| Method | Description |
|---|---|
| `populate()` | Fills all fields from `viewmodel.exam` |
| `on_upload_audio()` | File dialog → sets `audio_input` text (local path) |
| `on_attach_srt()` | Opens `.srt` file dialog → calls `parse_srt()` |
| `on_import_csv()` | Opens `.csv` file dialog, parses rows as `ExamSrtChunk` objects |
| `on_save()` | Syncs `audio_input` to `viewmodel.exam`, then calls `viewmodel.save_exam()` |
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

Full Groups & Questions panel. Layout loaded from [`ui/exam_groups_widget.ui`](../ui/exam_groups_widget.ui) via `pyside6-uic` → generates [`src/views/components/ui_exam_groups_widget.py`](../src/views/components/ui_exam_groups_widget.py).

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
| `q_list` | `QListWidget` | Question list (supports ExtendedSelection + right-click context menu) |
| `title_label` | `QLabel` | Right-panel title / selected question detail header |
| `listen_widget` | `QWidget` | Audio listen controls — hidden until a question with audio is selected |
| `listen_btn` | `QPushButton` | Play button for the question's audio segment |
| `status_label` | `QLabel` | Shows current audio segment timestamps |
| `passage_label` | `QLabel` | "Reading Passage" label — hidden for non-reading questions |
| `passage_browser` | `QTextBrowser` | Passage text display (yellow background) |
| `transcript_label` | `QLabel` | "Transcript Context" label — hidden until audio segment is set |
| `transcript_browser` | `QTextBrowser` | SRT chunk transcript for the selected audio segment |
| `options_scroll` | `QScrollArea` | Scrollable container for question option radio buttons |
| `options_container` | `QWidget` | Inner widget of `options_scroll` |
| `options_layout` | `QVBoxLayout` | Layout that holds `OptionWidget` instances |

#### Helper Classes

- **`TagMenuPopup`** — floating popup dialog (`QDialog` with `Popup | FramelessWindowHint`) for adding/removing tags on a question.
- **`SelectTranscriptDialog`** — dialog to select one or more SRT chunks to set the audio segment timestamps on a question.
- **`EditQuestionDialog`** — form dialog to edit question fields: Part, Correct Answer, Content, and Options A–D.
- **`EditContextDialog`** — inline editor dialog for editing `ExamContext` text content.
- **`OptionWidget`** — renders shuffled ABCD radio buttons for a single question. Options are shuffled per session for anti-cheat purposes; the correct answer is validated by original DB index, not display position.

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
| `_on_q_list_context_menu(pos)` | Right-click menu with Edit / Delete / Duplicate actions (filters actions based on item type) |
| `_on_edit_context()` | Opens `EditContextDialog` to modify the currently selected context |
| `_refresh_ctx_header_item(ctx)` | Refreshes the display text of a context header in the question list |
| `on_question_edited(updated_q)` | Called by `OptionWidget` after an inline question edit to refresh the list item text |
| `on_question_tag_changed()` | Called by `TagMenuPopup` to refresh the tag filter list |
| `on_question_audio_changed(question)` | Called by `OptionWidget` after saving a new audio segment |

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

Layout loaded from [`ui/exam_transcript_widget.ui`](../ui/exam_transcript_widget.ui) via `pyside6-uic` (compile step) → generates [`src/views/components/ui_exam_transcript_widget.py`](../src/views/components/ui_exam_transcript_widget.py).

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
| `save_btn` | `QPushButton` | Save changes — only visible when `_has_changes` is `True` |
| `table` | `QTableWidget` | 5-column SRT chunk table |
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
| `_on_item_changed(item)` | Syncs text column edits back to the chunk object |
| `_duplicate_chunk(chunk)` | Delegates to ViewModel, inserts new row at correct position |
| `_merge_chunk(chunk)` | Delegates to ViewModel, updates text/end in place, removes next row |
