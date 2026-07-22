# FSRS Learning Schedule Integration for Vocabulary

This plan outlines the changes needed to support FSRS scheduling for vocabulary learning in the SQLite and Supabase models, and updating the PySide6 view to filter vocabulary items that are due for learning today.

## User Review Required

> [!IMPORTANT]
> The SQLite database will be updated automatically via `init_db()` migration logic to add new columns to the `vocabulary` table. 
> Supabase sync should also include these columns in the serialization process.

## Proposed Changes

### 1. Domain Models

#### [MODIFY] [exam.py](file:///d:/my-project/workspace-anki/jun-edu/src/models/exam.py)
- Update `Vocabulary` Pydantic model to include FSRS fields:
  - `source_text: Optional[str] = None`
  - `ord: int = 0`
  - `due_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))`
  - `stability: float = 0.0`
  - `difficulty: float = 0.0`
  - `reps: int = 0`
  - `lapses: int = 0`
  - `step: Optional[int] = None`
  - `data: dict = Field(default_factory=dict)`
  - `state: int = 0`
  - `last_review_at: Optional[datetime.datetime] = None`
  - `updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))`

---

### 2. SQLite Database & ORM Models

#### [MODIFY] [orm_models.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/orm_models.py)
- Add the corresponding columns to the `Vocabulary` ORM class:
  - `source_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)`
  - `ord: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
  - `due_at: Mapped[str] = mapped_column(String, nullable=False, default=lambda: str(datetime.now(timezone.utc)))`
  - `stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)`
  - `difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)`
  - `reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
  - `lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
  - `step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)`
  - `data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)`
  - `state: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
  - `last_review_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)`
  - `updated_at: Mapped[str] = mapped_column(String, nullable=False, default=lambda: str(datetime.now(timezone.utc)))`

#### [MODIFY] [database.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/database.py)
- Update `init_db()` to automatically run `ALTER TABLE vocabulary ADD COLUMN ...` statements if any of the new fields are missing from the SQLite database.

---

### 3. Repository Updates

#### [MODIFY] [sqlite_repo.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/sqlite/sqlite_repo.py)
- Update `_vocabulary_from_orm()` to map all FSRS fields from the database to the pure `Vocabulary` model.
- Update `add_vocabulary()` to save/populate these fields (setting default FSRS state parameters, retrieving `source_text` from the context content if `context_id` is supplied).

#### [MODIFY] [supabase_repo.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/supabase/supabase_repo.py)
- Update `SupabaseExamRepository` to reflect the schema. Note that `SupabaseExamRepository` methods are placeholders raising `NotImplementedError`, but we should make sure we keep any class definitions aligned.

#### [MODIFY] [sync.py](file:///d:/my-project/workspace-anki/jun-edu/src/repositories/supabase/sync.py)
- Add `Vocabulary` to `SYNC_MODELS` so it gets synchronized to Supabase along with exams and attempts.

---

### 4. ViewModel & View Updates

#### [MODIFY] [vocabulary_list_viewmodel.py](file:///d:/my-project/workspace-anki/jun-edu/src/viewmodels/vocabulary_list_viewmodel.py)
- Add `due_only` boolean property.
- Add `set_due_only(self, val: bool)` method to toggle due filtering.
- Update `_apply_filter()` to filter vocabulary where `item.due_at <= now` if `due_only` is active.

#### [MODIFY] [vocabulary_list_view.ui](file:///d:/my-project/workspace-anki/jun-edu/ui/vocabulary_list_view.ui)
- Add a checkbox `due_only_checkbox` to the header layout.

#### [MODIFY] [vocabulary_list_view.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/vocabulary_list_view.py)
- Connect `due_only_checkbox.stateChanged` or `toggled` to `viewmodel.set_due_only`.

---

## Verification Plan

### Automated Tests
- Compile python files:
  ```powershell
  .\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"
  ```
- Run Pyright checking:
  ```powershell
  .\.venv\Scripts\python.exe -m pyright
  ```

### Manual Verification
- Run the app, go to Vocabulary List.
- Verify the "Due Today" filter toggles list correctly.
