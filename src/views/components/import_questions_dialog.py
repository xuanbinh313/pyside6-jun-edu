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

    # LLM prompt template
    PROMPT_TEXT = (
r'''
Analyze the attached exam image and extract all content into a structured JSON object
with two main arrays: "contexts" and "questions".

OBJECTIVE

- Identify if questions share a common context (reading passage, listening block,
  diagram, etc.).
- Always create at least ONE context entry for every question and link all
  questions to a context via
  "context_id".
- If a question is standalone (e.g. TOEIC Part 5), create a context entry with
  context_type "STANDALONE" and content { "text": "" }, then link that question
  to it. NEVER use null context_id.

OUTPUT FORMAT  (output ONLY raw JSON  no markdown, no code fences, no explanation)

{
  "contexts": [
    {
      "id": "<unique_string_id_you_create>",
      "part": <integer>,
      "context_type": "READING_PASSAGE",
      "content": { "text": "<full passage text with [[question_number]] placeholders>" },
      "index": 0
    }
  ],
  "questions": [
    {
      "context_id": "<must match an id from contexts array>",
      "content": "<question stem exactly as shown>",
      "options": ["<option text>", "..."],
      "correct_answer": "",
      "question_number": <integer>,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0, "note": "<why the correct answer is correct>" }
    }
  ]
}

FIELD RULES  contexts

id
  * A short unique string you invent (e.g. "ctx_1", "ctx_2").
  * Must be referenced exactly by questions that belong to this context.

context_type   choose ONE:
  * "READING_PASSAGE"   paragraphs, articles, emails, letters
  * "AUDIO_SRT"         listening transcripts / subtitles with timestamps
  * "IMAGE_DIAGRAM"     charts, maps, graphs, floor plans
  * "STANDALONE"        independent questions with no shared passage/audio/diagram

part
  * TOEIC part (1â€“7) or IELTS section as an integer.
  * Store part ONLY on the context, never on questions.

content   shape depends on context_type:
  * READING_PASSAGE   { "text": "<full passage text, replacing each blank '-------' or blank question indicator with [[question_number]] matching the corresponding question (e.g. [[131]])>" }
  * AUDIO_SRT         { "srt_lines": [ {"start": 0.0, "end": 2.5, "text": "..."}, ... ] }
  * IMAGE_DIAGRAM     { "text": "<describe the diagram briefly>" }
  * STANDALONE        { "text": "" }

index
  * Integer order in which this context appears in the image (0-based).

FIELD RULES  questions

context_id
  * Must match the "id" value of a context in the "contexts" array above.
  * Must NEVER be null. Standalone questions must reference a STANDALONE context.

content
  * Exact question stem as printed. For reading passage fill-in-the-blanks, you can set the stem to something simple or the question sentence if printed separately.
  * Preserve blanks (e.g. -----) and punctuation.

options
  * Flat array of strings.
  * REMOVE answer-label prefixes: (A), (B), A., B., etc.
  * Preserve original order.
  * Example: ["Home", "Work", "Travel", "School"]

correct_answer
  * REQUIRED. Must contain the answer choice label: "A", "B", "C", "D", etc.
  * If an answer key or marked answer is visible, use it.
  * If no answer key is visible, solve the question from the visible content and choose the best answer.
  * Never leave correct_answer empty.
  * If the image is too unclear to determine an answer, use "UNKNOWN" only as a last resort.

question_number
  * Printed question number as an integer.

question_type   choose ONE:
  * "MULTIPLE_CHOICE"
  * "FILL_IN_THE_BLANK"
  * "ESSAY"
  * "RECORDING"

additional_meta
  * Always include { "audio_start": 0.0, "audio_end": 0.0, "note": "<explanation>" }.
  * Fill in real timestamps only if shown in the image.
  * The note value is REQUIRED. Explain why correct_answer is correct using the
    visible context, question, grammar, vocabulary, or diagram evidence.

CONSTRAINTS
* Output ONLY the raw JSON object  no code blocks, no explanation, no markdown.
* Every question in the image must appear in the output.
* Every question must have a matching context_id.
* Every question must have correct_answer filled with the best answer label.
* Every question must have additional_meta.note explaining why the answer is correct.
* Do not leave correct_answer as "".
* If no shared context exists (e.g. Part 5 grammar), create a STANDALONE context
  for each standalone question or a group of standalone questions in the same part.

EXAMPLE OUTPUT (Part 6  reading passage + 2 questions)

{
  "contexts": [
    {
      "id": "ctx_1",
      "part": 6,
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
      "correct_answer": "A",
      "question_number": 131,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0, "note": "The phrase 'has been approved' needs a noun phrase subject, so 'your application' is correct." }
    },
    {
      "context_id": "ctx_1",
      "content": "-------",
      "options": ["any", "some", "few", "no"],
      "correct_answer": "A",
      "question_number": 132,
      "question_type": "MULTIPLE_CHOICE",
      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0, "note": "The plural noun 'questions' is used in an open condition, so 'any' is the natural determiner." }
    }
  ]
}
'''
    )

    VALID_CONTEXT_TYPES = {"READING_PASSAGE", "AUDIO_SRT", "IMAGE_DIAGRAM", "STANDALONE"}
    VALID_QUESTION_TYPES = {"MULTIPLE_CHOICE", "FILL_IN_THE_BLANK", "ESSAY", "RECORDING"}
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
            '{\n'
            '  "contexts": [\n'
            '    {\n'
            '      "id": "ctx_1",\n'
            '      "part": 6,\n'
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
            '      "question_number": 131,\n'
            '      "question_type": "MULTIPLE_CHOICE",\n'
            '      "additional_meta": { "audio_start": 0.0, "audio_end": 0.0, "note": "Explain why the selected answer is correct." }\n'
            '    }\n'
            '  ]\n'
            '}'
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
                "\"contexts\" and \"questions\"."
            )

        # â”€â”€ Parse contexts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            contexts.append({
                "llm_id":       llm_id,      # temporary reference key
                "part":         part,
                "context_type": ctx_type,
                "content":      content,
                "index":        index,
            })

        # â”€â”€ Parse questions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            # additional_meta (audio timestamps + answer explanation)
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
            additional_meta = {
                **meta_raw,
                "audio_start": audio_start,
                "audio_end": audio_end,
                "note": note,
            }

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
            q_type = str(q.get("question_type") or self.DEFAULT_QUESTION_TYPE).strip().upper()
            if q_type not in self.VALID_QUESTION_TYPES:
                q_type = self.DEFAULT_QUESTION_TYPE

            correct_answer = str(q.get("correct_answer") or "").strip().upper()

            # context_id  stored as llm reference; caller resolves to real uuid
            llm_ctx_id = q.get("context_id")
            if llm_ctx_id is not None:
                llm_ctx_id = str(llm_ctx_id).strip() or None

            questions.append({
                "llm_context_id":  llm_ctx_id,   # resolved by caller after DB insert of contexts
                "_legacy_part":    legacy_part,
                "content":         content,
                "options":         json.dumps(options_list, ensure_ascii=False),
                "correct_answer":  correct_answer,
                "question_number": question_number,
                "question_type":   q_type,
                "additional_meta": additional_meta,
            })

        context_ids = {ctx["llm_id"] for ctx in contexts}
        next_index = len(contexts)
        for q in questions:
            if q["llm_context_id"] in context_ids:
                continue
            standalone_id = f"standalone_{q['question_number'] or next_index}"
            while standalone_id in context_ids:
                standalone_id = f"standalone_{next_index}"
                next_index += 1
            contexts.append({
                "llm_id": standalone_id,
                "part": q.pop("_legacy_part", 1),
                "context_type": "STANDALONE",
                "content": {"text": ""},
                "index": next_index,
            })
            context_ids.add(standalone_id)
            q["llm_context_id"] = standalone_id
            next_index += 1

        for q in questions:
            q.pop("_legacy_part", None)

        return contexts, questions
