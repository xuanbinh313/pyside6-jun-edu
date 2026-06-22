import json

from json_repair import repair_json
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from ui_gen.ui_import_questions_dialog import Ui_ImportQuestionsDialog


class ImportQuestionsDialog(QDialog):
    """
    Two-step import dialog:
      Step 1  Copy a structured LLM prompt, send it to Gemini/ChatGPT with the exam image.
      Step 2  Paste the returned JSON object and click Import.

    The JSON response contains two arrays that map directly to DB models:
      - "contexts"   ExamContext  (part, context_type, content, index)
      - "questions"  ExamQuestion (context_id, content, options, correct_answer,
                                    question_number, question_type, additional_meta)
    """

    # Định nghĩa ngôn ngữ mặc định (Bạn có thể đổi thành "English", "Japanese", v.v.)
    TARGET_LANG = "Vietnamese (vn)"

    PROMPT_TEXT = r"""
Analyze the attached exam image and extract all content into a raw JSON object. 
OUTPUT CONSTRAINT: Output ONLY the raw JSON. No markdown, no ```json code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

{
    "contexts": [
        {
            "id": "Unique string ID (e.g., 'ctx_1', 'ctx_102')",
            "part": 6, // Integer (TOEIC part 1-7 or IELTS section). Store ONLY in context, NEVER in questions.
            "context_type": "READING_PASSAGE | IMAGE_DIAGRAM | STANDALONE",
            "content": {
                // READING_PASSAGE: Full text, replace blanks/indicators with placeholders like [[131]], [[132]]
                // IMAGE_DIAGRAM: Concise description of the chart/map/table
                // STANDALONE: Must be exactly {"text": ""}
                "text": "string"
            },
            "index": 0, // 0-based order of appearance in the image
            "additional_meta": { 
                "audio_start": 0.0, 
                "audio_end": 0.0, 
                "note": "REQUIRED. Provide the exact full translation of 'content.text' into {TARGET_LANG}. If STANDALONE, leave as empty string." 
            }
        }
    ],
    "questions": [
        {
            "context_id": "Must match a valid context id. NEVER null.",
            "question_number": 131, // Printed question number as integer
            "question_type": "MULTIPLE_CHOICE | FILL_IN_THE_BLANK | ESSAY | RECORDING",
            "content": "Exact stem. For reading blanks with no separate stem, use '-------'.",
            "options": ["Flat string array. Stripped of prefixes like (A), B., C), etc. Keep original order."],
            "correct_answer": "Required choice label ('A', 'B', etc.). Solve if unmarked. 'UNKNOWN' as last resort.",
            "additional_meta": {
                "note": "REQUIRED. Strictly format this field exactly as follows:\n[Translation of option 1 into {TARGET_LANG}]\n[Translation of option 2 into {TARGET_LANG}]\n[Translation of option 3 into {TARGET_LANG}]\n[Translation of option 4 into {TARGET_LANG}]\n\n[Detailed grammatical/contextual explanation in {TARGET_LANG} explaining why the correct_answer is right.]"
            }
        }
    ]
}

STRICT ARCHITECTURE RULES:
1. Every question must link to a context. Never use null context_id.
2. STANDALONE Questions: Every standalone question (e.g., TOEIC Part 5) MUST have its own unique, dedicated context entry (context_type: "STANDALONE", content: {"text": ""}). NEVER group multiple standalone questions into a single context.
3. SHARED Contexts: Questions sharing a passage or diagram must reference the exact same shared context ID.
4. Extract every visible question. Never leave correct_answer or additional_meta.note empty.
5. In 'questions.additional_meta.note', ensure there is a clear new line separating the option translations and the final explanation.
""".replace("{TARGET_LANG}", TARGET_LANG)

    VALID_CONTEXT_TYPES = {
        "READING_PASSAGE",
        "AUDIO_SRT",
        "IMAGE_DIAGRAM",
        "STANDALONE",
    }
    VALID_QUESTION_TYPES = {
        "MULTIPLE_CHOICE",
        "FILL_IN_THE_BLANK",
        "ESSAY",
        "RECORDING",
    }
    DEFAULT_QUESTION_TYPE = "MULTIPLE_CHOICE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Questions  LLM JSON Import")
        self.resize(720, 600)
        self.result_contexts: list[dict] = []
        self.result_questions: list[dict] = []
        self._setup_ui()

    # UI
    def _setup_ui(self):
        self.ui = Ui_ImportQuestionsDialog()
        self.ui.setupUi(self)

        self.prompt_edit = self.ui.prompt_edit
        self.json_edit = self.ui.json_edit
        self.prompt_edit.setText(self.PROMPT_TEXT)

        placeholder = (
            "{\n"
            '  "contexts": [\n'
            "    {\n"
            '      "id": "ctx_1",\n'
            '      "part": 6,\n'
            '      "context_type": "READING_PASSAGE",\n'
            '      "content": { "text": "..." },\n'
            '      "index": 0,\n'
            '      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0, "note": "" }\n'
            "    }\n"
            "  ],\n"
            '  "questions": [\n'
            "    {\n"
            '      "context_id": "ctx_1",\n'
            '      "content": "What is the topic?",\n'
            '      "options": ["Home", "Work", "Travel", "School"],\n'
            '      "correct_answer": "",\n'
            '      "question_number": 131,\n'
            '      "question_type": "MULTIPLE_CHOICE",\n'
            '      "additional_meta": { "note": "Explain why the selected answer is correct." }\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        self.json_edit.setPlaceholderText(placeholder)

        self.ui.copy_btn.clicked.connect(self._copy_prompt)
        self.ui.cancel_btn.clicked.connect(self.reject)
        self.ui.import_btn.clicked.connect(self._on_import)

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
                self,
                "JSON Parse Error",
                f"Could not parse the JSON.\n"
                f"Make sure it follows the template exactly.\n\nDetails: {exc}",
            )
            return

        if not questions:
            QMessageBox.warning(
                self, "No Data", "No questions found in the pasted JSON."
            )
            return

        self.result_contexts = contexts
        self.result_questions = questions
        self.accept()

    # JSON parser
    def _parse_json(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        """
        Parse the LLM-generated JSON object.

        Returns
        -------
        contexts : list[dict]
            Dicts ready to be passed to ExamContext constructor:
                part, context_type, content (dict/JSON), index
            The caller must supply exam_id before persisting.
            The 'llm_id' key carries the LLM-generated id so that the caller
            can build the mapping llm_id  real DB uuid.

        questions : list[dict]
            Dicts ready to be passed to ExamQuestion constructor:
                context_id (real DB uuid  resolved by caller),
                content, options (JSON string), correct_answer,
                question_number, question_type, additional_meta (dict)
            The 'llm_context_id' key carries the raw LLM reference before resolution.
            The caller must supply exam_id before persisting.
        """
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # LLM output sometimes contains unescaped quotes or other minor
            # JSON violations – attempt an automatic repair before giving up.
            data = json.loads(repair_json(raw_text))
        if not isinstance(data, dict):
            raise ValueError(
                "Expected a JSON object at the top level with keys "
                '"contexts" and "questions".'
            )

        # Parse contexts.
        raw_contexts = data.get("contexts", [])
        if not isinstance(raw_contexts, list):
            raise ValueError('"contexts" must be a JSON array.')

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

            try:
                part = int(ctx.get("part") or 1)
            except (TypeError, ValueError):
                part = 1

            content = ctx.get("content", {})
            if not isinstance(content, dict):
                # If a plain string was returned, normalise it
                content = {"text": str(content)}

            index = ctx.get("index", i)
            try:
                index = int(index)
            except (TypeError, ValueError):
                index = i

            meta_raw = ctx.get("additional_meta", {})
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
            ctx_meta = {
                "audio_start": audio_start,
                "audio_end": audio_end,
                "note": str(meta_raw.get("note", "")).strip(),
            }

            contexts.append(
                {
                    "llm_id": llm_id,  # temporary reference key
                    "part": part,
                    "context_type": ctx_type,
                    "content": content,
                    "index": index,
                    "additional_meta": ctx_meta,
                    "user_id": str(ctx.get("user_id")),
                }
            )

        # Parse questions.
        raw_questions = data.get("questions", [])
        if not isinstance(raw_questions, list):
            raise ValueError('"questions" must be a JSON array.')

        if not raw_questions:
            raise ValueError('The "questions" array is empty.')

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
                    options_list = [
                        o.strip() for o in options_raw.split(",") if o.strip()
                    ]
            else:
                options_list = []

            # additional_meta (only note for question, keep start/end as helper fields for fallback resolution)
            meta_raw = q.get("additional_meta", {})
            if not isinstance(meta_raw, dict):
                meta_raw = {}
            note = str(meta_raw.get("note") or q.get("note") or "").strip()
            try:
                audio_start = float(meta_raw.get("audio_start", 0.0))
            except (TypeError, ValueError):
                audio_start = 0.0
            try:
                audio_end = float(meta_raw.get("audio_end", 0.0))
            except (TypeError, ValueError):
                audio_end = 0.0

            # question_number
            try:
                legacy_part = int(q.get("part") or 1)
            except (TypeError, ValueError):
                legacy_part = 1
            try:
                question_number = int(q.get("question_number") or 0)
            except (TypeError, ValueError):
                question_number = 0

            # question_type
            q_type = (
                str(q.get("question_type") or self.DEFAULT_QUESTION_TYPE)
                .strip()
                .upper()
            )
            if q_type not in self.VALID_QUESTION_TYPES:
                q_type = self.DEFAULT_QUESTION_TYPE

            correct_answer = str(q.get("correct_answer") or "").strip().upper()

            # context_id  stored as llm reference; caller resolves to real uuid
            llm_ctx_id = q.get("context_id")
            if llm_ctx_id is not None:
                llm_ctx_id = str(llm_ctx_id).strip() or None

            questions.append(
                {
                    "llm_context_id": llm_ctx_id,  # resolved by caller after DB insert of contexts
                    "_legacy_part": legacy_part,
                    "content": content,
                    "options": json.dumps(options_list, ensure_ascii=False),
                    "correct_answer": correct_answer,
                    "question_number": question_number,
                    "question_type": q_type,
                    "additional_meta": {
                        "note": note,
                    },
                    "user_id": str(q.get("user_id")),
                    "_temp_audio_start": audio_start,
                    "_temp_audio_end": audio_end,
                }
            )

        # Resolve any audio start/end from questions to contexts if context doesn't have it
        for q in questions:
            llm_ctx_id = q.get("llm_context_id")
            if not llm_ctx_id:
                continue
            # Find matching context
            matching_ctx = next(
                (c for c in contexts if c["llm_id"] == llm_ctx_id), None
            )
            if matching_ctx:
                ctx_meta = matching_ctx.setdefault(
                    "additional_meta",
                    {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
                )
                q_start = q.pop("_temp_audio_start", 0.0)
                q_end = q.pop("_temp_audio_end", 0.0)
                if (q_start > 0.0 or q_end > 0.0) and ctx_meta.get(
                    "audio_end", 0.0
                ) == 0.0:
                    ctx_meta["audio_start"] = q_start
                    ctx_meta["audio_end"] = q_end
            else:
                q.pop("_temp_audio_start", None)
                q.pop("_temp_audio_end", None)

        context_ids = {ctx["llm_id"] for ctx in contexts}
        next_index = len(contexts)
        for q in questions:
            if q["llm_context_id"] in context_ids:
                continue
            standalone_id = f"standalone_{q['question_number'] or next_index}"
            while standalone_id in context_ids:
                standalone_id = f"standalone_{next_index}"
                next_index += 1
            contexts.append(
                {
                    "llm_id": standalone_id,
                    "part": q.pop("_legacy_part", 1),
                    "context_type": "STANDALONE",
                    "content": {"text": ""},
                    "index": next_index,
                    "additional_meta": {
                        "audio_start": 0.0,
                        "audio_end": 0.0,
                        "note": "",
                    },
                    "user_id": str(q.get("user_id")),
                }
            )
            context_ids.add(standalone_id)
            q["llm_context_id"] = standalone_id
            next_index += 1

        for q in questions:
            q.pop("_legacy_part", None)
            q.pop("_temp_audio_start", None)
            q.pop("_temp_audio_end", None)

        return contexts, questions
