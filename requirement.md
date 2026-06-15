# Implementation Plan — Multi-Exam Model & UI Update

## Background

The codebase is a PySide6 MVVM desktop app for exam management. It currently supports audio SRT chunk exams.
The new `exam.py` model has been extended with:
- `ExamContext` — stores passage/audio/image contexts (with JSON `content`)
- `ExamQuestion` — stores questions with `additional_meta` (JSON) for `audio_start`/`audio_end` timestamps and other metadata, plus `part`, `question_number`, `question_type`, `context_id`

The two target UI components (`exam_groups_widget.py`, `import_questions_dialog.py`) still reference **old** flat column attributes (`q.audio_start`, `q.audio_end`, `new_q = ExamQuestion(audio_start=..., audio_end=...)`) that **no longer exist** in the new model.

---

## Key Changes Required

### 1. Fix Model Reference Breakage

Old code references `q.audio_start` and `q.audio_end` as direct column fields.
New model stores them inside `ExamQuestion.additional_meta` as a JSON dict:
```python
additional_meta = {"audio_start": 12.34, "audio_end": 45.67}
```
Also, `ExamQuestion` now requires `part`, `question_number`, `question_type` fields.

---

## Proposed Changes

---

### `models/exam.py` — Fix `srt_chunks` back-reference

The `ExamSrtChunk` model has `exam = relationship("Exam", back_populates="srt_chunks")` but `Exam` does not have a `srt_chunks` relationship declared. Need to add it.

#### [MODIFY] [exam.py](file:///d:/my-project/workspace-anki/jun-edu/models/exam.py)
- Add `srt_chunks = relationship("ExamSrtChunk", back_populates="exam", cascade="all, delete-orphan")` to `Exam`

---

### `views/components/exam_groups_widget.py`

Major refactor required:

1. **`_on_question_selected`** — Replace `q.audio_start` / `q.audio_end` with `additional_meta` dict lookup:
   ```python
   meta = q.additional_meta or {}
   audio_start = meta.get("audio_start", 0.0)
   audio_end = meta.get("audio_end", 0.0)
   ```

2. **`_on_listen_clicked`** — Same fix for audio_start/audio_end access.

3. **`_on_import_questions_clicked`** — Replace `ExamQuestion(audio_start=..., audio_end=...)` with proper constructor using `additional_meta`, `part`, `question_number`, `question_type`, `context_id`:
   ```python
   new_q = ExamQuestion(
       exam_id=self.viewmodel.exam_id,
       part=q_data.get("part", 1),
       question_number=q_data.get("question_number", 0),
       question_type=q_data.get("question_type", "MULTIPLE_CHOICE"),
       context_id=q_data.get("context_id", None),
       content=q_data["content"],
       options=q_data["options"],
       correct_answer=q_data["correct_answer"],
       additional_meta={"audio_start": q_data["audio_start"], "audio_end": q_data["audio_end"]}
   )
   ```

4. **Add `ExamContext` rendering** — When a question has a `context_id`, load and render the context in the right panel:
   - For `READING_PASSAGE`: use `QTextBrowser` with `re.sub()` to parse `[[131]]` tags into clickable anchors
   - For `AUDIO_SRT`/listening: show the transcript panel

5. **Option shuffling (anti-cheat)** — Wrap options with `list(enumerate(options))`, shuffle, display with labels A/B/C/D, then validate against `correct_answer`.

6. **QScrollArea for questions** — Wrap the question options panel in `QScrollArea` to allow `ensureWidgetVisible()` for Reading Part 6/7 anchor clicks.

#### [MODIFY] [exam_groups_widget.py](file:///d:/my-project/workspace-anki/jun-edu/views/components/exam_groups_widget.py)

---

### `views/components/import_questions_dialog.py`

The CSV prompt and parser need to be updated:

1. **Prompt text** — Add `part`, `question_number`, `question_type`, `context_id` columns to the CSV template.

2. **Parser** — Read the new optional columns (with defaults), output them in `result_questions` dict.

3. **Header validation** — Accept the new extended CSV format while keeping backward compat (optional columns).

#### [MODIFY] [import_questions_dialog.py](file:///d:/my-project/workspace-anki/jun-edu/views/components/import_questions_dialog.py)

---

## Verification Plan

### Manual Verification
- Launch the app (`python mainwindow.py`)
- Open an existing exam → go to "Groups & Questions" tab
- Verify questions load correctly without `AttributeError`
- Click a question with audio metadata → verify "Listen" button appears with correct time range
- Click "Import Questions" → verify the dialog opens with updated prompt and parses the new CSV format
- Import a question with part/question_number fields → verify it saves without error
