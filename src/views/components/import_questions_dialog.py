import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QMessageBox, QApplication, QFrame
)
from PySide6.QtCore import Qt


class ImportQuestionsDialog(QDialog):
    """
    Two-step import dialog:
      Step 1 — Copy a structured LLM prompt, send it to Gemini/ChatGPT with the exam image.
      Step 2 — Paste the returned JSON object and click Import.

    The JSON response contains two arrays that map directly to DB models:
      - "contexts"  → ExamContext  (context_type, content, index)
      - "questions" → ExamQuestion (context_id, content, options, correct_answer,
                                    part, question_number, question_type, additional_meta)
    """

    # ── LLM prompt template ──────────────────────────────────────────────────
    PROMPT_TEXT = (
r'''
Analyze the attached exam image and extract all content into a structured JSON object
with two main arrays: "contexts" and "questions".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Identify if questions share a common context (reading passage, listening block,
  diagram, etc.).
- If they do, create ONE context entry and link all related questions to it via
  "context_id".
- If a question is standalone (e.g. TOEIC Part 5), set "context_id" to null and
  do NOT create a context entry.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT  (output ONLY raw JSON — no markdown, no code fences, no explanation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "contexts": [
    {
      "id": "<unique_string_id_you_create>",
      "context_type": "READING_PASSAGE",
      "content": { "text": "<full passage text with [[question_number]] placeholders>" },
      "index": 0
    }
  ],
  "questions": [
    {
      "context_id": "<must match an id from contexts array, or null>",
      "content": "<question stem exactly as shown>",
      "options": ["<option text>", "..."],
      "correct_answer": "",
      "part": <integer>,
      "question_number": <integer>,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0 }
    }
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD RULES — contexts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

id
  * A short unique string you invent (e.g. "ctx_1", "ctx_2").
  * Must be referenced exactly by questions that belong to this context.

context_type  — choose ONE:
  * "READING_PASSAGE"  — paragraphs, articles, emails, letters
  * "AUDIO_SRT"        — listening transcripts / subtitles with timestamps
  * "IMAGE_DIAGRAM"    — charts, maps, graphs, floor plans

content  — shape depends on context_type:
  * READING_PASSAGE  → { "text": "<full passage text, replacing each blank '-------' or blank question indicator with [[question_number]] matching the corresponding question (e.g. [[131]])>" }
  * AUDIO_SRT        → { "srt_lines": [ {"start": 0.0, "end": 2.5, "text": "..."}, ... ] }
  * IMAGE_DIAGRAM    → { "text": "<describe the diagram briefly>" }

index
  * Integer order in which this context appears in the image (0-based).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD RULES — questions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

context_id
  * Must match the "id" value of a context in the "contexts" array above.
  * Set to null if the question is independent (no shared context).

content
  * Exact question stem as printed. For reading passage fill-in-the-blanks, you can set the stem to something simple or the question sentence if printed separately.
  * Preserve blanks (e.g. -----) and punctuation.

options
  * Flat array of strings.
  * REMOVE answer-label prefixes: (A), (B), A., B., etc.
  * Preserve original order.
  * Example: ["Home", "Work", "Travel", "School"]

correct_answer
  * Leave as "" unless an answer key or marked answer is explicitly visible.
  * Never infer the answer.

part
  * TOEIC part (1–7) or IELTS section as an integer.

question_number
  * Printed question number as an integer.

question_type  — choose ONE:
  * "MULTIPLE_CHOICE"
  * "FILL_IN_THE_BLANK"
  * "ESSAY"
  * "RECORDING"

additional_meta
  * Always include { "audio_start": 0.0, "audio_end": 0.0 }.
  * Fill in real timestamps only if shown in the image.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

* Output ONLY the raw JSON object — no code blocks, no explanation, no markdown.
* Every question in the image must appear in the output.
* If no context exists (e.g. Part 5 grammar), set context_id to null and leave
  "contexts" as an empty array [].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OUTPUT (Part 6 — reading passage + 2 questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "contexts": [
    {
      "id": "ctx_1",
      "context_type": "READING_PASSAGE",
      "content": { "text": "Dear Mr. Smith,\nThank you for applying. We are pleased to inform you that [[131]] has been approved. Please contact us if you have [[132]] questions." },
      "index": 0
    }
  ],
  "questions": [
    {
      "context_id": "ctx_1",
      "content": "-------",
      "options": ["your application", "apply", "applicant", "applicable"],
      "correct_answer": "",
      "part": 6,
      "question_number": 131,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0 }
    },
    {
      "context_id": "ctx_1",
      "content": "-------",
      "options": ["any", "some", "few", "no"],
      "correct_answer": "",
      "part": 6,
      "question_number": 132,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0 }
    }
  ]
}
'''
    )

    # ── Field defaults ────────────────────────────────────────────────────────
    VALID_CONTEXT_TYPES = {"READING_PASSAGE", "AUDIO_SRT", "IMAGE_DIAGRAM"}
    VALID_QUESTION_TYPES = {"MULTIPLE_CHOICE", "FILL_IN_THE_BLANK", "ESSAY", "RECORDING"}
    DEFAULT_QUESTION_TYPE = "MULTIPLE_CHOICE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Questions — LLM JSON Import")
        self.resize(720, 600)
        self.result_contexts: list[dict] = []
        self.result_questions: list[dict] = []
        self._setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Step 1 ────────────────────────────────────────────────────────
        step1_title = QLabel("Step 1 — Copy prompt → paste into Gemini/ChatGPT with your exam image")
        step1_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1a73e8;")
        layout.addWidget(step1_title)

        desc = QLabel(
            "The LLM will extract contexts (passages, audio, diagrams) and questions "
            "as a structured JSON object, aligned with ExamContext and ExamQuestion models."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #5f6368; font-size: 12px;")
        layout.addWidget(desc)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setReadOnly(True)
        self.prompt_edit.setFixedHeight(160)
        self.prompt_edit.setStyleSheet(
            "background-color: #f8f9fa; border: 1px solid #dadce0; "
            "border-radius: 4px; font-family: monospace; font-size: 11px;"
        )
        self.prompt_edit.setText(self.PROMPT_TEXT)
        layout.addWidget(self.prompt_edit)

        copy_btn = QPushButton("📋  Copy Prompt to Clipboard")
        copy_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; font-weight: bold; padding: 6px 12px;"
            "border-radius: 4px;"
        )
        copy_btn.clicked.connect(self._copy_prompt)
        layout.addWidget(copy_btn)

        # ── Divider ───────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #dadce0;")
        layout.addWidget(line)

        # ── Step 2 ────────────────────────────────────────────────────────
        step2_title = QLabel("Step 2 — Paste the generated JSON data below and click Import")
        step2_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1a73e8;")
        layout.addWidget(step2_title)

        placeholder = (
            '{\n'
            '  "contexts": [\n'
            '    {\n'
            '      "id": "ctx_1",\n'
            '      "context_type": "READING_PASSAGE",\n'
            '      "content": { "text": "..." },\n'
            '      "index": 0\n'
            '    }\n'
            '  ],\n'
            '  "questions": [\n'
            '    {\n'
            '      "context_id": "ctx_1",\n'
            '      "content": "What is the topic?",\n'
            '      "options": ["Home", "Work", "Travel", "School"],\n'
            '      "correct_answer": "",\n'
            '      "part": 6,\n'
            '      "question_number": 131,\n'
            '      "question_type": "MULTIPLE_CHOICE",\n'
            '      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0 }\n'
            '    }\n'
            '  ]\n'
            '}'
        )
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText(placeholder)
        self.json_edit.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.json_edit)

        # ── Footer buttons ────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 6px 12px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        import_btn = QPushButton("✅  Import && Save")
        import_btn.setStyleSheet(
            "background-color: #34a853; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px;"
        )
        import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(import_btn)

        layout.addLayout(btn_layout)

    # ─────────────────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────────────────
    def _copy_prompt(self):
        QApplication.clipboard().setText(self.PROMPT_TEXT)
        QMessageBox.information(self, "Copied", "Prompt copied to clipboard!")

    def _on_import(self):
        raw = self.json_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Warning", "Please paste the JSON data first.")
            return

        try:
            contexts, questions = self._parse_json(raw)
        except Exception as exc:
            QMessageBox.critical(
                self, "JSON Parse Error",
                f"Could not parse the JSON.\n"
                f"Make sure it follows the template exactly.\n\nDetails: {exc}"
            )
            return

        if not questions:
            QMessageBox.warning(self, "No Data", "No questions found in the pasted JSON.")
            return

        self.result_contexts = contexts
        self.result_questions = questions
        self.accept()

    # ─────────────────────────────────────────────────────────────────────────
    # JSON parser
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_json(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        """
        Parse the LLM-generated JSON object.

        Returns
        -------
        contexts : list[dict]
            Dicts ready to be passed to ExamContext constructor:
                context_type, content (dict/JSON), index
            The caller must supply exam_id before persisting.
            The 'llm_id' key carries the LLM-generated id so that the caller
            can build the mapping llm_id → real DB uuid.

        questions : list[dict]
            Dicts ready to be passed to ExamQuestion constructor:
                context_id (real DB uuid or None — resolved by caller),
                content, options (JSON string), correct_answer,
                part, question_number, question_type, additional_meta (dict)
            The 'llm_context_id' key carries the raw LLM reference before resolution.
            The caller must supply exam_id before persisting.
        """
        data = json.loads(raw_text)
        if not isinstance(data, dict):
            raise ValueError(
                "Expected a JSON object at the top level with keys "
                "\"contexts\" and \"questions\"."
            )

        # ── Parse contexts ─────────────────────────────────────────────────
        raw_contexts = data.get("contexts", [])
        if not isinstance(raw_contexts, list):
            raise ValueError("\"contexts\" must be a JSON array.")

        contexts: list[dict] = []
        for i, ctx in enumerate(raw_contexts):
            if not isinstance(ctx, dict):
                continue

            llm_id = str(ctx.get("id", f"ctx_{i}")).strip()
            if not llm_id:
                llm_id = f"ctx_{i}"

            ctx_type = str(ctx.get("context_type", "READING_PASSAGE")).strip().upper()
            if ctx_type not in self.VALID_CONTEXT_TYPES:
                ctx_type = "READING_PASSAGE"

            content = ctx.get("content", {})
            if not isinstance(content, dict):
                # If a plain string was returned, normalise it
                content = {"text": str(content)}

            index = ctx.get("index", i)
            try:
                index = int(index)
            except (TypeError, ValueError):
                index = i

            contexts.append({
                "llm_id":       llm_id,      # temporary reference key
                "context_type": ctx_type,
                "content":      content,
                "index":        index,
            })

        # ── Parse questions ────────────────────────────────────────────────
        raw_questions = data.get("questions", [])
        if not isinstance(raw_questions, list):
            raise ValueError("\"questions\" must be a JSON array.")

        if not raw_questions:
            raise ValueError("The \"questions\" array is empty.")

        questions: list[dict] = []
        for q in raw_questions:
            if not isinstance(q, dict):
                continue

            content = str(q.get("content", "")).strip()
            if not content:
                continue

            # options
            options_raw = q.get("options", [])
            if isinstance(options_raw, list):
                options_list = [str(o) for o in options_raw]
            elif isinstance(options_raw, str):
                try:
                    options_list = json.loads(options_raw)
                    if not isinstance(options_list, list):
                        raise ValueError
                except Exception:
                    options_list = [o.strip() for o in options_raw.split(",") if o.strip()]
            else:
                options_list = []

            # additional_meta (audio timestamps + any future fields)
            meta_raw = q.get("additional_meta", {})
            if not isinstance(meta_raw, dict):
                meta_raw = {}
            try:
                audio_start = float(meta_raw.get("audio_start", 0.0))
            except (TypeError, ValueError):
                audio_start = 0.0
            try:
                audio_end = float(meta_raw.get("audio_end", 0.0))
            except (TypeError, ValueError):
                audio_end = 0.0
            additional_meta = {**meta_raw, "audio_start": audio_start, "audio_end": audio_end}

            # part & question_number
            try:
                part = int(q.get("part") or 1)
            except (TypeError, ValueError):
                part = 1
            try:
                question_number = int(q.get("question_number") or 0)
            except (TypeError, ValueError):
                question_number = 0

            # question_type
            q_type = str(q.get("question_type") or self.DEFAULT_QUESTION_TYPE).strip().upper()
            if q_type not in self.VALID_QUESTION_TYPES:
                q_type = self.DEFAULT_QUESTION_TYPE

            correct_answer = str(q.get("correct_answer") or "").strip().upper()

            # context_id — stored as llm reference; caller resolves to real uuid
            llm_ctx_id = q.get("context_id")
            if llm_ctx_id is not None:
                llm_ctx_id = str(llm_ctx_id).strip() or None

            questions.append({
                "llm_context_id":  llm_ctx_id,   # resolved by caller after DB insert of contexts
                "content":         content,
                "options":         json.dumps(options_list, ensure_ascii=False),
                "correct_answer":  correct_answer,
                "part":            part,
                "question_number": question_number,
                "question_type":   q_type,
                "additional_meta": additional_meta,
            })

        return contexts, questions
