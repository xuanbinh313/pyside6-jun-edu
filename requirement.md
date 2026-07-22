# Implementation Plan - Refactor `srt_chunks` to `Exam` Table Column

Refactor the `srt_chunks` storage model so that transcript chunks are stored directly in a column on the `Exam` table (`Text`/JSON-string in SQLite, `jsonb` in Supabase) rather than maintaining a separate `exam_srt_chunks` child table. Additionally, update the Supabase sync service to exclude `exam_srt_chunks` from synced models and handle the `srt_chunks` JSON serialization/deserialization for `Exam` sync operations.

## User Review Required

> [!NOTE]
> - **SQLite Schema Migration**: An `ALTER TABLE exams ADD COLUMN srt_chunks TEXT` migration will be automatically executed in `init_db()` for existing local databases so existing SQLite databases upgrade gracefully.
> - **Supabase Schema**: In Supabase PostgreSQL, the `exams` table `srt_chunks` column is assumed to be `jsonb`. The sync service will handle converting between Python objects / JSON strings in SQLite and JSONB arrays in Supabase.
> - **Clean MVVM Separation**: Hand-written views and viewmodels already access `srt_chunks` via domain models (`Exam.srt_chunks` / `IExamRepository` methods `replace_srt_chunks` and `list_srt_chunks`). They will continue to work seamlessly without breaking signature changes.

## Open Questions

None. The requirements are clear and well-aligned with the existing architecture.

## Proposed Changes

---

### Database Schema & Models

#### [MODIFY] [orm_models.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/repositories/sqlite/orm_models.py)
- Add `srt_chunks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to `orm.Exam`.
- Remove `orm.ExamSrtChunk` model and the `srt_chunks` relationship on `orm.Exam`.

#### [MODIFY] [database.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/repositories/sqlite/database.py)
- Add dynamic SQLite migration check in `init_db()`:
  - Check if `srt_chunks` column exists in `exams` table; if not, run `ALTER TABLE exams ADD COLUMN srt_chunks TEXT`.

#### [MODIFY] [exam.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/models/exam.py)
- Ensure `Exam` Pydantic model's `srt_chunks: list[ExamSrtChunk] = Field(default_factory=list)` remains intact and serializes/deserializes correctly when mapped from ORM data.

---

### Repository Layer

#### [MODIFY] [sqlite_repo.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/repositories/sqlite/sqlite_repo.py)
- Update `_exam_from_orm`: parse `db_exam.srt_chunks` JSON string into `list[ExamSrtChunk]` and assign to `Exam.srt_chunks`.
- Update `get_exam_details(exam_id)`: load `srt_chunks` directly from `db_exam.srt_chunks` instead of querying `orm.ExamSrtChunk`.
- Update `get_exam_take_data(exam_id, user_id)`: read `srt_chunks` from `db_exam.srt_chunks` instead of querying `orm.ExamSrtChunk`.
- Update `replace_srt_chunks(exam_id, chunks)`: serialize `chunks` to a JSON string, save into `db_exam.srt_chunks`, and set `db_exam.dirty = True`.
- Update `list_srt_chunks(exam_id)`: parse `db_exam.srt_chunks` JSON string and return `list[ExamSrtChunk]`.
- Update `save_external_aligned_exam(...)`: store aligned segments as JSON string directly into `exam.srt_chunks` instead of inserting `orm.ExamSrtChunk` records.

---

### Supabase Sync Service

#### [MODIFY] [sync.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/repositories/supabase/sync.py)
- Remove `ExamSrtChunk` from `SYNC_MODELS` so the `exam_srt_chunks` table is no longer synced.
- Update `_serialize_row`: when serializing `Exam` model for Supabase push, convert `srt_chunks` JSON string or `list` into native Python `list` payload so Supabase REST API writes `jsonb`.
- Update `_deserialize_row`: when deserializing `Exam` row pulled from Supabase, convert `srt_chunks` list payload into a JSON string for SQLite storage.

---

### Codebase Audit (Widgets, Views & ViewModels)

#### [MODIFY] [exam_details_viewmodel.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/viewmodels/exam_details_viewmodel.py)
#### [MODIFY] [exam_transcript_viewmodel.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/viewmodels/exam_transcript_viewmodel.py)
#### [MODIFY] [select_transcript_viewmodel.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/viewmodels/select_transcript_viewmodel.py)
#### [MODIFY] [exam_take_viewmodel.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/viewmodels/exam_take_viewmodel.py)
#### [MODIFY] [exam_take_view.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/exam_take_view.py)
#### [MODIFY] [exam_form_widget.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/components/exam_form_widget.py)
#### [MODIFY] [exam_transcript_widget.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/components/exam_transcript_widget.py)
- Audit all calls to ensure compatibility with `Exam.srt_chunks` list representation.
- Verify `replace_srt_chunks` and `list_srt_chunks` calls work seamlessly without expecting `exam_srt_chunks` table ORM entities.

---

## Verification Plan

### Automated Tests & Syntax Check
- Run Python syntax validation script across `src/` directory:
  ```powershell
  .\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src',) for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"
  ```
- Run Pyright typing check:
  ```powershell
  .\.venv\Scripts\python.exe -m pyright
  ```

### Manual Verification
- Test loading, editing, saving SRT chunks in Exam details and transcript editing widgets.
- Test exam take view flow for dictation/transcript loading.
- Test sync service push/pull logic to ensure `Exam.srt_chunks` syncs correctly with Supabase `jsonb`.
