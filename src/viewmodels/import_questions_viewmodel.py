import csv
import io
import json
import re
from pathlib import Path

from json_repair import repair_json
from PySide6.QtCore import QObject, Signal


class ImportQuestionsViewModel(QObject):
    state_changed = Signal()

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_contexts: list[dict] = []
        self.result_questions: list[dict] = []
        self.result_answer_key: dict[int, str] = {}
        self.selected_image_paths: list[str] = []
        self.question_numbers_text = ""
        self.prompt_texts = self._build_prompt_texts()

    def _build_prompt_texts(self) -> dict[str, str]:
        return {
            "listening": self.LISTENING_PROMPT_TEXT,
            "reading": self.READING_PROMPT_TEXT,
            "answer_sheet": self.ANSWER_SHEET_PROMPT_TEXT,
        }

    def prompt_text(self, prompt_key: str) -> str:
        return self.prompt_texts.get(prompt_key, "")

    def set_prompt_text(self, prompt_key: str, text: str) -> None:
        self.prompt_texts[prompt_key] = text

    def set_selected_image_paths(self, paths: list[str]) -> None:
        self.selected_image_paths = list(paths)
        self.state_changed.emit()

    def selected_image_count_label(self) -> str:
        if not self.selected_image_paths:
            return "No images selected"
        return f"{len(self.selected_image_paths)} image(s) selected"

    def default_question_numbers_text(self) -> str:
        return ",".join(str(i) for i in range(1, len(self.selected_image_paths) + 1))

    def set_question_numbers_text(self, text: str) -> None:
        self.question_numbers_text = text

    def parse_import(
        self, raw_json: str, answer_csv: str, question_numbers_text: str
    ) -> tuple[list[dict], list[dict], dict[int, str]]:
        self.question_numbers_text = question_numbers_text
        raw_json = raw_json.strip()
        answer_csv = answer_csv.strip()
        if not raw_json and not self.selected_image_paths and not answer_csv:
            raise ValueError("Please paste JSON question data or answer key CSV first.")

        contexts: list[dict] = []
        questions: list[dict] = []
        if raw_json or self.selected_image_paths:
            contexts, questions = self.parse_json(raw_json)

        answer_key = self.parse_answer_key_csv(answer_csv)
        if not questions and not answer_key:
            raise ValueError("No questions found in the pasted JSON.")

        duplicate_numbers = self.duplicate_question_numbers(questions)
        if duplicate_numbers:
            duplicate_text = ", ".join(f"Q{number}" for number in duplicate_numbers)
            raise ValueError(
                "The import data contains duplicate question number(s): "
                f"{duplicate_text}.\nPlease keep each question number unique in the "
                "import JSON."
            )

        if answer_key:
            self.apply_answer_key_to_questions(questions, answer_key)

        self.result_contexts = contexts
        self.result_questions = questions
        self.result_answer_key = answer_key
        self.state_changed.emit()
        return contexts, questions, answer_key

    def parse_answer_key_csv(self, raw_text: str) -> dict[int, str]:
        if not raw_text:
            return {}

        clean_text = re.sub(r"^```(?:csv)?\s*|\s*```$", "", raw_text.strip())
        reader = csv.DictReader(io.StringIO(clean_text))
        if not reader.fieldnames:
            raise ValueError("CSV header is missing.")

        normalized_fields = {
            str(field or "").strip().lower(): field for field in reader.fieldnames
        }
        question_field = normalized_fields.get("question")
        answer_field = normalized_fields.get("answer")
        if not question_field or not answer_field:
            raise ValueError('CSV header must include "question" and "answer".')

        answer_key: dict[int, str] = {}
        for row_number, row in enumerate(reader, start=2):
            raw_question = str(row.get(question_field, "")).strip()
            raw_answer = str(row.get(answer_field, "")).strip().upper()
            if not raw_question and not raw_answer:
                continue
            try:
                question_number = int(raw_question)
            except ValueError as exc:
                raise ValueError(
                    f"Row {row_number} has invalid question number: {raw_question}"
                ) from exc
            if question_number <= 0:
                raise ValueError(f"Row {row_number} question must be greater than zero.")

            answer_match = re.search(r"[A-D]", raw_answer)
            if not answer_match:
                continue
            answer_key[question_number] = answer_match.group(0)
        return answer_key

    def apply_answer_key_to_questions(
        self, questions: list[dict], answer_key: dict[int, str]
    ) -> None:
        for question in questions:
            try:
                question_number = int(question.get("question_number", 0) or 0)
            except (TypeError, ValueError):
                continue
            answer = answer_key.get(question_number)
            if answer:
                question["correct_answer"] = answer

    def parse_json(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        try:
            data = self.parse_json_object(raw_text)
        except json.JSONDecodeError:
            data = json.loads(repair_json(raw_text))
        if not isinstance(data, dict):
            raise ValueError(
                "Expected a JSON object at the top level with keys "
                '"contexts" and "questions".'
            )

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
                    "llm_id": llm_id,
                    "part": part,
                    "context_type": ctx_type,
                    "content": content,
                    "index": index,
                    "additional_meta": ctx_meta,
                    "user_id": str(ctx.get("user_id")),
                }
            )

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

            try:
                legacy_part = int(q.get("part") or 1)
            except (TypeError, ValueError):
                legacy_part = 1
            try:
                question_number = int(q.get("question_number") or 0)
            except (TypeError, ValueError):
                question_number = 0

            q_type = (
                str(q.get("question_type") or self.DEFAULT_QUESTION_TYPE)
                .strip()
                .upper()
            )
            if q_type not in self.VALID_QUESTION_TYPES:
                q_type = self.DEFAULT_QUESTION_TYPE

            correct_answer = str(q.get("correct_answer") or "").strip().upper()

            llm_ctx_id = q.get("context_id")
            if llm_ctx_id is not None:
                llm_ctx_id = str(llm_ctx_id).strip() or None

            questions.append(
                {
                    "llm_context_id": llm_ctx_id,
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

        for q in questions:
            llm_ctx_id = q.get("llm_context_id")
            if not llm_ctx_id:
                continue
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

        return self.merge_image_diagrams(contexts, questions)

    def duplicate_question_numbers(self, questions: list[dict]) -> list[int]:
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

    def parse_question_numbers(self) -> list[int]:
        if not self.selected_image_paths:
            return []
        raw = self.question_numbers_text.strip()
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

    def parse_json_object(self, raw_text: str) -> dict:
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

    def default_question(self, question_number: int, llm_context_id: str) -> dict:
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

    def merge_image_diagrams(
        self, contexts: list[dict], questions: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        if not self.selected_image_paths:
            return contexts, questions

        question_numbers = self.parse_question_numbers()
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
                        "_source_image_path": image_path,
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
                    question_number, self.default_question(question_number, llm_id)
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
