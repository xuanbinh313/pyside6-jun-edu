from typing import Optional, Protocol, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from src.viewmodels.import_questions_viewmodel import ImportQuestionsViewModel
from ui_gen.ui_import_questions_dialog import Ui_ImportQuestionsDialog


class PluginPageRegistry(Protocol):
    def get_page(self, plugin_id: str, page_id: str) -> object:
        ...

    def request_page(self, plugin_id: str, page_id: str) -> None:
        ...


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

    ANSWER_SHEET_PROMPT_TEXT = r"""
Analyze the attached answer sheet image and extract only the printed answer key.
OUTPUT CONSTRAINT: Output ONLY CSV text. No markdown, no code fences, no explanations.

CSV FORMAT:
question,answer
1,A
2,B
3,C

RULES:
1. The first row must be exactly: question,answer
2. Use the printed question number as an integer.
3. Use only answer letters A, B, C, or D.
4. If an answer cannot be read confidently, omit that row.
5. Do not include duplicate question rows.
"""

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

    def __init__(
        self, parent=None, viewmodel: Optional[ImportQuestionsViewModel] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Import Questions  LLM JSON Import")
        self.resize(720, 600)
        self.viewmodel = viewmodel or ImportQuestionsViewModel(self)
        self._setup_ui()

    @property
    def result_contexts(self) -> list[dict]:
        return self.viewmodel.result_contexts

    @property
    def result_questions(self) -> list[dict]:
        return self.viewmodel.result_questions

    @property
    def result_answer_key(self) -> dict[int, str]:
        return self.viewmodel.result_answer_key

    @property
    def selected_image_paths(self) -> list[str]:
        return self.viewmodel.selected_image_paths

    # UI
    def _setup_ui(self):
        self.ui = Ui_ImportQuestionsDialog()
        self.ui.setupUi(self)

        self.prompt_edit = self.ui.prompt_edit
        self.json_edit = self.ui.json_edit
        self.prompt_texts = self.viewmodel.prompt_texts
        self._setup_prompt_list()
        self._setup_plugin_actions()
        self._setup_image_picker()
        self._setup_answer_key_input()

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

    def _setup_plugin_actions(self) -> None:
        action_row = QHBoxLayout()
        self.open_agent_plugin_btn = QPushButton("Open Agent Plugin", self)
        self.open_agent_plugin_btn.setToolTip(
            "Open the plugin-provided agent import workspace"
        )
        self.open_agent_plugin_btn.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #dadce0; border-radius: 4px;"
        )
        self.open_ocr_plugin_btn = QPushButton("Open OCR Plugin", self)
        self.open_ocr_plugin_btn.setToolTip("Open the plugin-provided OCR workspace")
        self.open_ocr_plugin_btn.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #dadce0; border-radius: 4px;"
        )
        action_row.addWidget(self.open_agent_plugin_btn)
        action_row.addWidget(self.open_ocr_plugin_btn)
        action_row.addStretch(1)
        self.ui.main_layout.insertLayout(3, action_row)

        self.open_agent_plugin_btn.clicked.connect(
            lambda: self._open_plugin_page("agent", "dashboard", "Agent")
        )
        self.open_ocr_plugin_btn.clicked.connect(
            lambda: self._open_plugin_page("ocr", "dashboard", "OCR")
        )

    def _plugin_registry(self) -> Optional[PluginPageRegistry]:
        current = self.parent()
        while current is not None:
            registry = getattr(current, "plugin_ui_registry", None)
            if registry is not None:
                return cast(PluginPageRegistry, registry)
            current = current.parent()
        return None

    def _open_plugin_page(
        self, plugin_id: str, page_id: str, plugin_title: str
    ) -> None:
        registry = self._plugin_registry()
        if registry is None:
            QMessageBox.warning(
                self,
                f"{plugin_title} Plugin Unavailable",
                "Plugin services are not available from this window.",
            )
            return

        try:
            registry.get_page(plugin_id, page_id)
        except KeyError:
            QMessageBox.warning(
                self,
                f"{plugin_title} Plugin Unavailable",
                f"The {plugin_title} plugin is missing or disabled.",
            )
            return

        registry.request_page(plugin_id, page_id)
        self.reject()

    def _build_prompt_texts(self) -> dict[str, str]:
        return self.viewmodel.prompt_texts

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
            ("answer_sheet", "Answer sheet - CSV question,answer"),
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

    def _setup_answer_key_input(self):
        answer_label = QLabel("Answer key CSV:")
        answer_label.setStyleSheet("color: #3c4043; font-size: 12px;")
        self.answer_key_edit = QTextEdit()
        self.answer_key_edit.setMinimumHeight(92)
        self.answer_key_edit.setMaximumHeight(140)
        self.answer_key_edit.setPlaceholderText("question,answer\n1,A\n2,B\n3,C")
        self.answer_key_edit.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; "
            "font-family: monospace; font-size: 11px;"
        )
        divider_index = self.ui.main_layout.indexOf(self.ui.divider_line)
        self.ui.main_layout.insertWidget(divider_index, answer_label)
        self.ui.main_layout.insertWidget(divider_index + 1, self.answer_key_edit)

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
        self.viewmodel.set_selected_image_paths(files)
        self.image_count_label.setText(self.viewmodel.selected_image_count_label())
        self.question_numbers_input.setText(
            self.viewmodel.default_question_numbers_text()
        )

    def _on_import(self):
        raw = self.json_edit.toPlainText().strip()
        answer_csv = self.answer_key_edit.toPlainText().strip()
        if not raw and not self.selected_image_paths and not answer_csv:
            QMessageBox.warning(
                self,
                "Warning",
                "Please paste JSON question data or answer key CSV first.",
            )
            return

        try:
            self.viewmodel.parse_import(
                raw, answer_csv, self.question_numbers_input.text().strip()
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))
            return

        self.accept()

    def _parse_answer_key_csv(self, raw_text: str) -> dict[int, str]:
        return self.viewmodel.parse_answer_key_csv(raw_text)

    def _apply_answer_key_to_questions(
        self, questions: list[dict], answer_key: dict[int, str]
    ) -> None:
        self.viewmodel.apply_answer_key_to_questions(questions, answer_key)

    def _parse_json(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        return self.viewmodel.parse_json(raw_text)

    def _duplicate_question_numbers(self, questions: list[dict]) -> list[int]:
        return self.viewmodel.duplicate_question_numbers(questions)

    def _parse_question_numbers(self) -> list[int]:
        self.viewmodel.set_question_numbers_text(self.question_numbers_input.text())
        return self.viewmodel.parse_question_numbers()

    def _parse_json_object(self, raw_text: str) -> dict:
        return self.viewmodel.parse_json_object(raw_text)

    def _default_question(self, question_number: int, llm_context_id: str) -> dict:
        return self.viewmodel.default_question(question_number, llm_context_id)

    def _merge_image_diagrams(
        self, contexts: list[dict], questions: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        self.viewmodel.set_question_numbers_text(self.question_numbers_input.text())
        return self.viewmodel.merge_image_diagrams(contexts, questions)
