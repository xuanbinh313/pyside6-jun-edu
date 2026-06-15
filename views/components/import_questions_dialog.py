import csv
import io
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
      Step 2 — Paste the returned CSV and click Import.

    CSV columns (aligned with ExamQuestion model):
        content, options, correct_answer, part, question_number,
        question_type, context_id, audio_start, audio_end
    """

    # ── LLM prompt template ──────────────────────────────────────────────────
    PROMPT_TEXT = (
        "Analyze the attached exam image and extract all multiple-choice questions "
        "into a raw CSV format.\n"
        "Do NOT output markdown code blocks or extra text — output ONLY the raw CSV "
        "using exactly the headers below:\n\n"
        "content,options,correct_answer,part,question_number,question_type,"
        "context_id,audio_start,audio_end\n\n"
        "Example row:\n"
        '"What is the topic?","[\\"A. Home\\",\\"B. Work\\",\\"C. Travel\\",\\"D. School\\"]",'
        '"A",1,101,"MULTIPLE_CHOICE",,12.5,18.2\n\n'
        "Column rules:\n"
        "1. content       — The question stem text.\n"
        "2. options       — A valid JSON array of strings (4 elements, properly escaped).\n"
        "3. correct_answer— The letter of the correct option: A, B, C, or D.\n"
        "4. part          — TOEIC part number (1–7) or IELTS section number. Integer.\n"
        "5. question_number— The display number printed on the exam (e.g. 101). Integer.\n"
        "6. question_type — One of: MULTIPLE_CHOICE, FILL_IN_THE_BLANK, ESSAY, RECORDING.\n"
        "7. context_id    — Leave EMPTY unless you know the DB UUID of a shared context.\n"
        "8. audio_start   — Seconds float (start of audio clip). Default 0.0 if unknown.\n"
        "9. audio_end     — Seconds float (end of audio clip).   Default 0.0 if unknown.\n"
    )

    REQUIRED_COLUMNS = ["content", "options", "correct_answer"]
    OPTIONAL_COLUMNS = {
        "part": 1,
        "question_number": 0,
        "question_type": "MULTIPLE_CHOICE",
        "context_id": "",
        "audio_start": 0.0,
        "audio_end": 0.0,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Questions — LLM CSV Import")
        self.resize(700, 560)
        self.result_questions = []
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
            "The LLM will extract all questions and format them as CSV matching the "
            "ExamQuestion model (part, question_number, audio timestamps, etc.)."
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
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #dadce0;")
        layout.addWidget(line)

        # ── Step 2 ────────────────────────────────────────────────────────
        step2_title = QLabel("Step 2 — Paste the generated CSV data below and click Import")
        step2_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1a73e8;")
        layout.addWidget(step2_title)

        placeholder = (
            "content,options,correct_answer,part,question_number,"
            "question_type,context_id,audio_start,audio_end\n"
            '"Question stem?","[\\"A. Opt1\\",\\"B. Opt2\\",\\"C. Opt3\\",\\"D. Opt4\\"]",'
            '"B",1,101,"MULTIPLE_CHOICE",,12.5,18.2'
        )
        self.csv_edit = QTextEdit()
        self.csv_edit.setPlaceholderText(placeholder)
        self.csv_edit.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.csv_edit)

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
        raw = self.csv_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Warning", "Please paste the CSV data first.")
            return

        try:
            parsed = self._parse_csv(raw)
        except Exception as exc:
            QMessageBox.critical(
                self, "CSV Parse Error",
                f"Could not parse the CSV.\n"
                f"Make sure it follows the template exactly.\n\nDetails: {exc}"
            )
            return

        if not parsed:
            QMessageBox.warning(self, "No Data", "No questions found in the pasted CSV.")
            return

        self.result_questions = parsed
        self.accept()

    # ─────────────────────────────────────────────────────────────────────────
    # CSV parser
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_csv(self, raw_text: str) -> list[dict]:
        """
        Parse the LLM-generated CSV and return a list of question dicts.

        Required columns : content, options, correct_answer
        Optional columns (with defaults from OPTIONAL_COLUMNS):
            part, question_number, question_type, context_id,
            audio_start, audio_end
        """
        reader = csv.reader(io.StringIO(raw_text))
        header_row = next(reader, None)
        if header_row is None:
            raise ValueError("CSV appears to be empty.")

        header = [h.strip().lower() for h in header_row]

        # Validate required columns
        for col in self.REQUIRED_COLUMNS:
            if col not in header:
                raise ValueError(f"Missing required column: '{col}'")

        # Build index map
        idx = {col: header.index(col) for col in header}

        def _get(row, col, default=None):
            """Safe column fetch with fallback."""
            i = idx.get(col)
            if i is None or i >= len(row):
                return default
            val = row[i].strip()
            return val if val else default

        parsed = []
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue  # skip blank rows

            content = _get(row, "content", "")
            if not content:
                continue

            # Parse options JSON
            options_raw = _get(row, "options", "[]")
            try:
                options_list = json.loads(options_raw)
                if not isinstance(options_list, list):
                    raise ValueError("options must be a JSON array")
            except Exception:
                # Graceful fallback: split by comma if JSON parse fails
                options_list = [
                    o.strip().strip('"')
                    for o in options_raw.strip("[]").split(",")
                    if o.strip()
                ]

            # audio timestamps
            try:
                audio_start = float(_get(row, "audio_start", "0.0"))
            except (TypeError, ValueError):
                audio_start = 0.0
            try:
                audio_end = float(_get(row, "audio_end", "0.0"))
            except (TypeError, ValueError):
                audio_end = 0.0

            # part & question_number
            try:
                part = int(_get(row, "part", str(self.OPTIONAL_COLUMNS["part"])))
            except (TypeError, ValueError):
                part = self.OPTIONAL_COLUMNS["part"]
            try:
                question_number = int(
                    _get(row, "question_number",
                         str(self.OPTIONAL_COLUMNS["question_number"]))
                )
            except (TypeError, ValueError):
                question_number = self.OPTIONAL_COLUMNS["question_number"]

            question_type = _get(row, "question_type",
                                 self.OPTIONAL_COLUMNS["question_type"])
            context_id    = _get(row, "context_id", "") or ""

            parsed.append({
                "content":         content,
                "options":         json.dumps(options_list, ensure_ascii=False),
                "correct_answer":  _get(row, "correct_answer", "A").strip().upper(),
                "part":            part,
                "question_number": question_number,
                "question_type":   question_type,
                "context_id":      context_id,
                "audio_start":     audio_start,
                "audio_end":       audio_end,
            })

        return parsed
