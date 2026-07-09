# Create Vocabulary List View (LingQ-Style Table)

This plan outlines the changes needed to introduce a Vocabulary List View, displaying vocabulary items in a LingQ-style table containing the text word, meaning, source context text, and status levels with interactive buttons.

## User Review Required

> [!IMPORTANT]
> - We will run an inline SQL command on startup to ensure existing SQLite databases receive the new `meaning` and `status` columns in the `vocabulary` table if they do not exist already.
> - The vocabulary status levels will be represented by buttons 1, 2, 3, 4, and a Check icon (learned/known), color-coded to match LingQ's progress visual styling.

## Proposed Changes

### 1. Database & Model Schema

#### [MODIFY] [orm_models.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/orm_models.py)
- Add column `meaning` to `Vocabulary` (`Mapped[Optional[str]] = mapped_column(String, nullable=True)`).
- Add column `status` to `Vocabulary` (`Mapped[int] = mapped_column(Integer, nullable=False, default=1)`).
- Add relationship `context` to `Vocabulary` targeting `ExamContext` so we can retrieve the source text from the parent context.

#### [MODIFY] [exam.py](file:///d:/my-project/workspace-anki/jun-edu/src/models/exam.py)
- Update `Vocabulary` schema model:
  - Add fields `meaning: Optional[str] = None` and `status: int = 1`.
  - Add optional field `source_text: Optional[str] = None`.

#### [MODIFY] [database.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/database.py)
- Update `init_db()` to automatically check and run `ALTER TABLE vocabulary ADD COLUMN ...` queries for both `meaning` and `status` columns to prevent migration errors for existing databases.

### 2. Repository Layer

#### [MODIFY] [base_repo.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/base_repo.py)
Add abstract methods for CRUD actions on vocabulary items:
- `list_vocabulary(self) -> list[Vocabulary]`
- `update_vocabulary_status(self, vocab_id: str, status: int) -> None`
- `update_vocabulary_meaning(self, vocab_id: str, meaning: str) -> None`
- `delete_vocabulary(self, vocab_id: str) -> None`

#### [MODIFY] [sqlite_repo.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/sqlite_repo.py)
- Implement `_vocabulary_from_orm` to dynamically load `source_text` from `db_vocabulary.context.content["text"]` if available.
- Implement methods for listing, updating status, updating meaning, and deleting vocabulary records.

### 3. ViewModel Layer

#### [NEW] [vocabulary_list_viewmodel.py](file:///d:/my-project/workspace-anki/jun-edu/src/viewmodels/vocabulary_list_viewmodel.py)
Create `VocabularyListViewModel` owning state, loading list items, and exposing triggers for:
- Fetching vocabulary items (with optional search/filtering).
- Changing vocabulary status (1, 2, 3, 4, 5).
- Updating vocabulary meaning.
- Deleting vocabulary items.

### 4. View Layer

#### [NEW] [vocabulary_list_view.ui](file:///d:/my-project/workspace-anki/jun-edu/ui/vocabulary_list_view.ui)
Create a new Qt Designer UI file:
- Layout with a search bar at the top, a back button to main menu, and a `QTableWidget` to show the list of words.

#### [NEW] [ui_vocabulary_list_view.py](file:///d:/my-project/workspace-anki/jun-edu/ui_gen/ui_vocabulary_list_view.py)
- Generate code module from `vocabulary_list_view.ui`.

#### [NEW] [vocabulary_list_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/vocabulary_list_view.py)
Implement the hand-written PySide6 View:
- Use a `QTableWidget` to display text, meaning (double-click to edit, or custom delegate/editor), source context text, and the status controls.
- Create custom cell widgets for status buttons:
  - Button 1: Red/Orange background when selected, otherwise gray/border.
  - Button 2: Orange background when selected.
  - Button 3: Yellow background when selected.
  - Button 4: Light Green background when selected.
  - Button 5 (Check Icon): Green background when selected.
  - Delete Button (Trash Icon): Red color.
- Wire up interactive buttons to call viewmodel methods.
- Filter list as user types in the search bar.

#### [MODIFY] [main_window.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/main_window.py)
- Import `VocabularyListView` and its ViewModel.
- Register action in `setup_menu_bar` (e.g. "Vocabulary List" under Menu) that navigates the stacked widget to the vocabulary list.

## Verification Plan

### Manual Verification
1. Open application and select the "Vocabulary List" action from the Menu.
2. Confirm the table matches LingQ style layout.
3. Edit a meaning column cell, press enter, and check if it persists.
4. Click status buttons (1, 2, 3, 4, or Check icon) and verify the button styling updates to show active state.
5. Click the trash icon to delete a word, and ensure the word disappears from the list.
6. Verify database updates occur successfully.
