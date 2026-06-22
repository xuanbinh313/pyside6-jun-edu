# Migration of Audio Segment Metadata from ExamQuestion to ExamContext

This plan outlines the changes needed to move the audio timestamp metadata (`audio_start` and `audio_end`) from individual questions (`ExamQuestion`) to their shared contexts (`ExamContext`).

## User Review Required

> [!IMPORTANT]
> The database schema changes require updates to SQLAlchemy model configurations. If an existing local SQLite database exists, it will need to have the `additional_meta` column added to the `exam_contexts` table. We should handle this gracefully in `src/models/database.py` via schema checks, or inform you how to recreate it.

## Proposed Changes

---

### [Models]

#### [MODIFY] [exam.py](file:///d:/my-project/workspace-anki/jun-edu/src/models/exam.py)
- Define a new `QuestionAdditionalMeta` TypedDict containing only `note`.
- Keep `AdditionalMeta` TypedDict as is (containing `audio_start`, `audio_end`, and `note`).
- Update `ExamContext` model to add `additional_meta: Mapped[AdditionalMeta] = mapped_column(JSON, default=lambda: {"audio_start": 0.0, "audio_end": 0.0, "note": ""})`.
- Update `ExamQuestion` model to change type of `additional_meta` to `QuestionAdditionalMeta` and default to `lambda: {"note": ""}`.

#### [MODIFY] [database.py](file:///d:/my-project/workspace-anki/jun-edu/src/models/database.py)
- Update `_ensure_schema_columns()` to automatically check and add `additional_meta` to `exam_contexts` if it is missing, making sure existing SQLite databases do not crash.

---

### [Helpers]

#### [MODIFY] [helpers.py](file:///d:/my-project/workspace-anki/jun-edu/src/utils/helpers.py)
- Update `get_audio_meta(question)` to retrieve the audio timestamps from `question.context.additional_meta` if `question.context` is available, falling back to `question.additional_meta` (for backward compatibility).

---

### [Views & Components]

#### [MODIFY] [add_exam_question_dialog.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/components/add_exam_question_dialog.py)
- Remove question-level audio start/end fields and selectors from `_setup_question_forms()`, `_add_question_form()`, `_populate_question_form()`, and saving methods.
- Update `_populate_from_context()` to read `audio_start` and `audio_end` from `context.additional_meta` instead of `context.content`.
- Update `_context_content()` to exclude `audio_start` and `audio_end` from the content dictionary.
- In `_on_save()`, save `audio_start` and `audio_end` to `db_ctx.additional_meta`.
- Clean up `_add_question_audio_selector`, `_on_select_question_audio_segment`, `_set_question_audio_segment` since audio selection is now handled strictly at the context level.

#### [MODIFY] [exam_groups_widget.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/components/exam_groups_widget.py)
- Update `_on_listen_clicked` to play audio using the context's `additional_meta` (retrieving it via `ctx.additional_meta` or fallback).
- In `_questions_for_context()`, eager load the `context` relation using `joinedload` so that `question.context` is loaded before expunging.
- In `_on_import_questions_clicked`, pass `additional_meta` (containing audio segment info) when creating the `ExamContext` row.

#### [MODIFY] [import_questions_dialog.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/components/import_questions_dialog.py)
- Update `PROMPT_TEXT` template to instruct the LLM to output `additional_meta` on `contexts` instead of `questions` (the prompt will guide the LLM to output `audio_start`/`audio_end` in the context's metadata, and only `note` in the question's metadata).
- Update `_parse_json` to parse `additional_meta` from the LLM context entries.
- Add fallback logic in `_parse_json` that if the LLM output places `audio_start` or `audio_end` on questions instead of contexts, it copies those values to the context's `additional_meta` and strips them from the question.

#### [MODIFY] [option_question_item.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/components/option_question_item.py)
- Update `_on_select_audio_segment` to save selected transcript timestamps to `db_q.context.additional_meta` instead of `db_q.additional_meta`.

---

### [Documentation]

#### [MODIFY] [models.md](file:///d:/my-project/workspace-anki/jun-edu/docs/models.md)
- Update documentation schema tables to reflect the new structure.

## Verification Plan

### Automated Tests
- Run Python syntax compile check:
  ```powershell
  .\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"
  ```

### Manual Verification
- Open the application and create/edit an exam.
- Add questions and context to verify context-level audio segment selection works.
- Verify playback of context audio segments works as expected.
- Verify prompt copy and paste JSON import works, checking both new and legacy formats.
