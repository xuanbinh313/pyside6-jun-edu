import json
from pathlib import Path

from json_repair import repair_json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

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

    LISTENING_PROMPT_TEXT = r"""
Analyze the attached listening transcript text and extract all content into a raw JSON object. 
OUTPUT CONSTRAINT: Output ONLY the raw JSON. No markdown, no ```json code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

{
    "contexts": [
        {
            "id": "Unique string ID (e.g., 'ctx_l1_1', 'ctx_l3_32')",
            "part": 2, // Integer (TOEIC part 1, 2, 3, or 4). Store ONLY in context, NEVER in questions.
            "context_type": "AUDIO_SRT | STANDALONE",
            "content": {
                // AUDIO_SRT: For Part 3 & 4. Put the full conversation/talk transcript text here.
                // STANDALONE: For Part 1 & 2. Must be exactly {"text": ""}
                "text": "string"
            },
            "index": 0, // 0-based order of appearance in the transcript
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
            "question_number": 11, // Printed or spoken question number as integer
            "question_type": "MULTIPLE_CHOICE",
            "content": "Question stem text. Follow the LISTENING PART RULES below.",
            "options": ["Flat string array. Stripped of prefixes like (A), B., C), etc. Keep original order."],
            "correct_answer": "Required choice label ('A', 'B', 'C', or 'D').",
            "additional_meta": {
                "note": "REQUIRED. Strictly format this field exactly as follows:\n[Translation of the question content stem into {TARGET_LANG}]\n[Translation of option 1 into {TARGET_LANG}]\n[Translation of option 2 into {TARGET_LANG}]\n[Translation of option 3 into {TARGET_LANG}]\n[Translation of option 4 into {TARGET_LANG} (if applicable)]\n\n[Detailed grammatical/contextual explanation in {TARGET_LANG} explaining why the correct_answer is right based on keywords from the transcript.]"
            }
        }
    ]
}

LISTENING PART RULES:
1. PART 1 (Photographs):
   - context_type: "STANDALONE" (content.text = "")
   - questions.content: Set to exactly "Look at the picture and choose the statement that best describes it."
   - questions.options: Put the 4 transcript descriptions (A, B, C, D) here.

2. PART 2 (Question-Response):
   - context_type: "STANDALONE" (content.text = "")
   - questions.content: Put the spoken Question/Statement here (e.g., "Where is the meeting room?").
   - questions.options: Put the 3 spoken response choices (A, B, C) here.

3. PART 3 & 4 (Conversations & Talks):
   - context_type: "AUDIO_SRT"
   - contexts.content.text: Put the entire spoken dialogue or monologue transcript block here.
   - questions.content: Put the printed question stem here.
   - questions.options: Put the 4 printed multiple-choice options here.

STRICT ARCHITECTURE RULES:
1. Every question must link to a context. Never use null context_id.
2. For Part 1 and Part 2, every single question MUST have its own unique, dedicated "STANDALONE" context. Do NOT group multiple Part 1 or Part 2 questions into one context.
3. For Part 3 and Part 4, all questions belonging to the same conversation/talk (usually sets of 3) must reference the exact same shared "AUDIO_SRT" context ID.
4. Extract every question provided in the transcript. Never leave correct_answer or additional_meta.note empty.
5. In 'questions.additional_meta.note', ensure there is a clear new line separating the translations (question + options) and the final explanation.
""".replace("{TARGET_LANG}", TARGET_LANG)

    READING_PROMPT_TEXT = r"""
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

    PROMPT_TEXT = READING_PROMPT_TEXT

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
        self.selected_image_paths: list[str] = []
        self._setup_ui()

    # UI
    def _setup_ui(self):
        self.ui = Ui_ImportQuestionsDialog()
        self.ui.setupUi(self)

        self.prompt_edit = self.ui.prompt_edit
        self.json_edit = self.ui.json_edit
        self.prompt_texts = self._build_prompt_texts()
        self._setup_prompt_list()
        self._setup_image_picker()

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

    def _build_prompt_texts(self) -> dict[str, str]:
        return {
            "listening": self.LISTENING_PROMPT_TEXT,
            "reading": self.READING_PROMPT_TEXT,
        }

    def _setup_prompt_list(self):
        self.ui.step1_title.setText("Step 1 - Choose a prompt to copy or edit")
        self.ui.description_label.setText(
            "Select the matching TOEIC part, review the prompt, copy it to your LLM, then paste the generated JSON below."
        )
        self.prompt_edit.hide()
        self.ui.copy_btn.setText("Open Selected Prompt")

        self.prompt_list = QListWidget()
        self.prompt_list.setMinimumHeight(132)
        self.prompt_list.setMaximumHeight(160)
        self.prompt_list.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; background: white;"
        )
        prompt_labels = [
            ("listening", "TOEIC Parts 1-4 - Listening transcript"),
            ("reading", "TOEIC Part 5,6,7 - Reading comprehension"),
        ]
        for key, label in prompt_labels:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.prompt_list.addItem(item)
        self.prompt_list.setCurrentRow(1)
        self.prompt_list.itemClicked.connect(self._open_prompt_editor)
        self.ui.main_layout.insertWidget(2, self.prompt_list)

    def _setup_image_picker(self):
        image_row = QHBoxLayout()
        self.pick_images_btn = QPushButton("Select Diagram Images")
        self.pick_images_btn.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #dadce0; border-radius: 4px;"
        )
        self.pick_images_btn.clicked.connect(self._pick_images)
        image_row.addWidget(self.pick_images_btn)

        self.image_count_label = QLabel("No images selected")
        self.image_count_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        image_row.addWidget(self.image_count_label, 1)
        divider_index = self.ui.main_layout.indexOf(self.ui.divider_line)
        self.ui.main_layout.insertLayout(divider_index, image_row)

        numbers_row = QHBoxLayout()
        numbers_label = QLabel("Question numbers:")
        numbers_label.setStyleSheet("color: #3c4043; font-size: 12px;")
        numbers_row.addWidget(numbers_label)

        self.question_numbers_input = QLineEdit()
        self.question_numbers_input.setPlaceholderText(
            "Auto-filled from selected images, e.g. 1,2,3"
        )
        self.question_numbers_input.setStyleSheet(
            "padding: 5px 8px; border: 1px solid #dadce0; border-radius: 4px;"
        )
        numbers_row.addWidget(self.question_numbers_input, 1)
        self.ui.main_layout.insertLayout(divider_index + 1, numbers_row)

    def _copy_prompt(self):
        current_item = self.prompt_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "No Prompt", "Please select a prompt first.")
            return
        self._open_prompt_editor(current_item)

    def _open_prompt_editor(self, item: QListWidgetItem):
        prompt_key = item.data(Qt.ItemDataRole.UserRole)
        if not prompt_key:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(item.text())
        dialog.resize(760, 560)

        layout = QVBoxLayout(dialog)
        editor = QTextEdit(dialog)
        editor.setPlainText(self.prompt_texts.get(prompt_key, ""))
        editor.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; "
            "font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(editor)

        button_row = QHBoxLayout()
        copy_btn = QPushButton("Copy to Clipboard", dialog)
        copy_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; font-weight: bold; "
            "padding: 6px 12px; border-radius: 4px;"
        )
        close_btn = QPushButton("Close", dialog)
        close_btn.setStyleSheet("padding: 6px 12px;")
        button_row.addStretch(1)
        button_row.addWidget(copy_btn)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        def copy_current_prompt():
            current_text = editor.toPlainText()
            self.prompt_texts[prompt_key] = current_text
            QApplication.clipboard().setText(current_text)
            QMessageBox.information(dialog, "Copied", "Prompt copied to clipboard!")

        copy_btn.clicked.connect(copy_current_prompt)
        close_btn.clicked.connect(dialog.accept)

        dialog.exec()
        self.prompt_texts[prompt_key] = editor.toPlainText()

    def _pick_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select IMAGE_DIAGRAM files",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if not files:
            return
        self.selected_image_paths = files
        self.image_count_label.setText(f"{len(files)} image(s) selected")
        default_numbers = ",".join(str(i) for i in range(1, len(files) + 1))
        self.question_numbers_input.setText(default_numbers)

    def _on_import(self):
        raw = self.json_edit.toPlainText().strip()
        if not raw and not self.selected_image_paths:
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
        duplicate_numbers = self._duplicate_question_numbers(questions)
        if duplicate_numbers:
            duplicate_text = ", ".join(f"Q{number}" for number in duplicate_numbers)
            QMessageBox.warning(
                self,
                "Duplicate Question Numbers",
                f"The import data contains duplicate question number(s): {duplicate_text}.\n"
                "Please keep each question number unique in the import JSON.",
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
            data = self._parse_json_object(raw_text)
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

        if not raw_questions and not self.selected_image_paths:
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

        return self._merge_image_diagrams(contexts, questions)

    def _duplicate_question_numbers(self, questions: list[dict]) -> list[int]:
        seen: set[int] = set()
        duplicates: set[int] = set()
        for question in questions:
            try:
                number = int(question.get("question_number", 0) or 0)
            except (TypeError, ValueError):
                continue
            if number <= 0:
                continue
            if number in seen:
                duplicates.add(number)
            seen.add(number)
        return sorted(duplicates)

    def _parse_question_numbers(self) -> list[int]:
        if not self.selected_image_paths:
            return []
        raw = self.question_numbers_input.text().strip()
        if not raw:
            return list(range(1, len(self.selected_image_paths) + 1))

        numbers: list[int] = []
        for token in raw.replace("\n", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                number = int(token)
            except ValueError as exc:
                raise ValueError(f"Invalid question number: {token}") from exc
            if number <= 0:
                raise ValueError("Question numbers must be greater than zero.")
            numbers.append(number)

        if len(numbers) > len(self.selected_image_paths):
            raise ValueError(
                "Question number count cannot be greater than selected image count."
            )
        return numbers or list(range(1, len(self.selected_image_paths) + 1))

    def _parse_json_object(self, raw_text: str) -> dict:
        if not raw_text:
            return {"contexts": [], "questions": []}
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            data = json.loads(repair_json(raw_text))
        if not isinstance(data, dict):
            raise ValueError(
                "Expected a JSON object at the top level with keys "
                '"contexts" and "questions".'
            )
        return data

    def _default_question(self, question_number: int, llm_context_id: str) -> dict:
        return {
            "llm_context_id": llm_context_id,
            "content": "",
            "options": json.dumps(["", "", "", ""], ensure_ascii=False),
            "correct_answer": "",
            "question_number": question_number,
            "question_type": self.DEFAULT_QUESTION_TYPE,
            "additional_meta": {"note": ""},
            "user_id": "None",
        }

    def _merge_image_diagrams(
        self, contexts: list[dict], questions: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        if not self.selected_image_paths:
            return contexts, questions

        question_numbers = self._parse_question_numbers()
        question_by_number = {
            int(q.get("question_number", 0)): q
            for q in questions
            if int(q.get("question_number", 0) or 0) > 0
        }

        image_contexts: list[dict] = []
        image_questions: list[dict] = []
        for index, image_path in enumerate(self.selected_image_paths):
            llm_id = f"image_ctx_{index + 1}"
            image_contexts.append(
                {
                    "llm_id": llm_id,
                    "part": 1,
                    "context_type": "IMAGE_DIAGRAM",
                    "content": {
                        "text": Path(image_path).stem,
                        "image_path": image_path,
                        "image_filename": Path(image_path).name,
                    },
                    "index": index,
                    "additional_meta": {
                        "audio_start": 0.0,
                        "audio_end": 0.0,
                        "note": "",
                    },
                    "user_id": "None",
                }
            )

            if index >= len(question_numbers):
                continue
            question_number = question_numbers[index]
            question = dict(
                question_by_number.get(
                    question_number, self._default_question(question_number, llm_id)
                )
            )
            question["llm_context_id"] = llm_id
            question["question_number"] = question_number
            options = question.get("options", "[]")
            if isinstance(options, str):
                try:
                    options_list = json.loads(options)
                except Exception:
                    options_list = []
            elif isinstance(options, list):
                options_list = options
            else:
                options_list = []
            options_list = [str(option) for option in options_list[:4]]
            options_list.extend([""] * (4 - len(options_list)))
            question["options"] = json.dumps(options_list, ensure_ascii=False)
            question["content"] = str(question.get("content", ""))
            question["correct_answer"] = str(question.get("correct_answer", ""))
            question["question_type"] = question.get(
                "question_type", self.DEFAULT_QUESTION_TYPE
            )
            meta = question.get("additional_meta") or {"note": ""}
            if not isinstance(meta, dict):
                meta = {"note": ""}
            question["additional_meta"] = {"note": str(meta.get("note", ""))}
            image_questions.append(question)

        return image_contexts, image_questions
