Here is the updated implementation plan for your review:

# Implementation Plan - Vocabulary List View Update

This plan outlines the changes to [vocabulary_list_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/vocabulary_list_view.py) to replace the QTableWidget with a modern, responsive card-based layout, and to add a button for auto-translating vocabulary words with empty meanings using the Gemini AI agent API.

## Proposed Changes

### View Layer

#### [MODIFY] [vocabulary_list_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/vocabulary_list_view.py)

- **UI Setup**:
  - Remove the table widget `self.ui.table` from the layout programmatically (or ignore it) and replace it with a dynamically populated `QScrollArea`. Set its widget resizable to `True`.
  - Create a container `QWidget` with a `QVBoxLayout` inside the scroll area to hold the cards.
  - Create a new header button `self.translate_button = QPushButton("AI Translate Empty")` with a robot icon (`fa5s.robot`) and add it to `self.ui.header_layout` next to the search bar.
- **Card Rendering**:
  - Update `_populate()` to clear the card container layout instead of table row items.
  - For each `Vocabulary` item, create a custom `QFrame` card:
    - **Styling**: Sleek card layout (border, padding, border-radius, background colors).
    - **Word**: Bold title label.
    - **Meaning / Edit Mode**: 
      - Initially show the meaning as a read-only `QLabel` next to an **"Edit"** button.
      - Clicking the "Edit" button replaces the label with a `QLineEdit` and changes the button to a "Save" icon/text.
      - Editing is saved to the database calling `self.viewmodel.update_meaning(vocab.id, line_edit.text())`, reverting the field back to a read-only label.
    - **Source Context**: Word-wrapped secondary text label.
    - **Status**: The 5-button status indicator widget.
    - **Delete**: Trash icon button.
- **AI Translation Handler**:
  - Add a worker class `VocabularyTranslateWorker(QThread)` inside `vocabulary_list_view.py` or as a helper:
    - Queries the words needing translation.
    - Calls the Gemini API using `google.genai` with system instructions to translate the vocabulary words to Vietnamese.
    - Emits a signal with the translations or updates them via the viewmodel.
  - Connect the translate button to spawn the worker, showing a progress dialog or status message during the translation process.
  - Call `self.viewmodel.load_vocabulary()` once completed.

## Verification Plan

### Automated Tests
- Run syntax validation check:
  `.\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"`
- Run Pyright strict typing check:
  `.\.venv\Scripts\python.exe -m pyright`

### Manual Verification
1. Open the vocabulary view in the app and verify the list is displayed as elegant cards.
2. Edit a meaning inside a card's text field and check that it updates/saves.
3. Click "AI Translate Empty" and verify that words with empty meanings get automated Vietnamese translations filled in.