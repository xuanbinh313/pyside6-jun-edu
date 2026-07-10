# Implementation Plan - Dictation Exercise Feature

This plan outlines the implementation of a new "Dictation" exercise feature within the Exam Take View. It allows users to practice and learn transcripts by typing what they hear, with precise character-level diff highlighting using the `diff-match-patch` library.

## User Review Required

> [!IMPORTANT]
> - The new "Dictation" mode will load the SRT (transcript) chunks associated with the exam.
> - An interactive `ExerciseDictationView` will be displayed when the user clicks "Start Dictation".
> - Character-level comparison will use `diff-match-patch` to highlight omitted/incorrect characters in red strikethrough and inserted characters in blue.
> - Normalizing text (ignoring extra whitespace and smart quotes) will be performed before comparing for the correctness check.

## Proposed Changes

---

### 1. Database & ViewModel Layer

#### [MODIFY] [exam_take_viewmodel.py](file:///d:/my-project/workspace-anki/jun-edu/src/viewmodels/exam_take_viewmodel.py)
- Update `load_exam()` to query and load `ExamSrtChunk` records associated with the current `exam_id` from the database.
- Store these chunks as `self.srt_chunks: List[ExamSrtChunk] = []`.
- Expose properties/methods to retrieve the list of srt chunks for dictation.

---

### 2. View Layer

#### [NEW] [exercise_dictation_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/exercise_dictation_view.py)
Create `ExerciseDictationView` subclassing `QWidget`:
- **Audio Playback**: Embed a `QMediaPlayer` and `QAudioOutput` to handle range-based playback using the `start_time` and `end_time` (converted to milliseconds) from the selected `ExamSrtChunk`.
- **Top Right Navigation**: Next/Prev buttons with icons (e.g. using `qtawesome` icons) to cycle through the chunks.
- **Audio Control**: A prominent "Play" button to play/replay the current chunk's audio segment.
- **Multi-line Dictation Input**: A `QTextEdit` input. Install an event filter or subclass it to capture `Enter`/`Return` (without Shift/Ctrl) to submit the typed text.
- **Correctness Evaluation**:
  - Compare user input to `chunk.text` (case-insensitive and ignoring punctuation differences).
  - Show a status label ("Correct!" in green or "Incorrect" in red).
  - Use `diff-match-patch` to compute differences and display a beautiful HTML representation in a read-only `QTextEdit` or `QLabel` below, highlighting insertions (blue background) and deletions (red background with strikethrough).

#### [MODIFY] [exam_take_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/exam_take_view.py)
- Import `ExerciseDictationView`.
- In `_setup_pages()`, initialize `dictation_page` and add it to `self.ui.stacked_widget`.
- In `_mode_tabs()`, add a third tab labeled `"Dictation"` next to `"Real Test"`.
- Implement `_dictation_tab()` returning a page containing exam transcript info, warning message if no transcripts/audio exist, and a `"Start Dictation"` button.
- Wire the `"Start Dictation"` button to switch the stacked widget to the dictation exercise screen and trigger audio playback of the first chunk.
- Update `_on_back_clicked` to handle returning from the dictation screen to the overview page.

---

## Verification Plan

### Automated Tests
- Syntax validation check:
  `.\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"`
- Pyright strict typing check:
  `.\.venv\Scripts\python.exe -m pyright`

### Manual Verification
1. Navigate to an exam details page and choose to take the exam.
2. Select the "Dictation" tab next to the "Real Test" tab.
3. Click "Start Dictation". Verify it loads the dictation page and plays the first chunk's audio.
4. Test navigation using the Prev/Next buttons.
5. Type in the input text area and press Enter. Verify the comparison output displays with correct/incorrect status and beautiful character-level diff highlights.
