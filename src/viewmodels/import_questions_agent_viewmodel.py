from __future__ import annotations
from src.utils.helpers import get_local_media_dir

import os
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, QThread, Signal

from src.viewmodels.import_questions_viewmodel import ImportQuestionsViewModel

load_dotenv()


class AgentPartPayload(BaseModel):
    part: int
    question_pdf_path: str = ""
    question_pages: list[int] = Field(default_factory=list)
    transcript_pdf_path: str = ""
    transcript_pages: list[int] = Field(default_factory=list)
    prompt: str = ""
    context_text: str = ""


class AgentAnswerSheetPayload(BaseModel):
    listening_image_path: str = ""
    reading_image_path: str = ""
    prompt: str = ""


class AgentImportPayload(BaseModel):
    parts: list[AgentPartPayload] = Field(default_factory=list)
    answer_sheet: AgentAnswerSheetPayload = Field(
        default_factory=AgentAnswerSheetPayload
    )


class AgentImportResult(BaseModel):
    contexts: list[dict] = Field(default_factory=list)
    questions: list[dict] = Field(default_factory=list)
    answer_key: dict[int, str] = Field(default_factory=dict)


class AgentPartResult(BaseModel):
    response_text: str
    image_paths: list[str] = Field(default_factory=list)


class ImportQuestionsAgentWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, payload: AgentImportPayload, parser: ImportQuestionsViewModel):
        super().__init__()
        self.payload = payload
        self.parser = parser

    def run(self):
        try:
            result = self._run_agent()
            self.finished.emit(result.model_dump())
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agent(self) -> AgentImportResult:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "").strip()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env.")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is not set in .env.")
        if not location:
            raise ValueError("GOOGLE_CLOUD_LOCATION is not set in .env.")

        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("google-genai is not installed.") from exc

        client = genai.Client(api_key=api_key)

        result = AgentImportResult()
        with get_local_media_dir() as tmp_dir:
            for part_payload in self.payload.parts:
                if not self._has_part_input(part_payload):
                    continue
                self.progress.emit(f"Preparing Part {part_payload.part} files...")
                part_result = self._generate_part(
                    client, model_name, part_payload, tmp_dir
                )
                contexts, questions = self.parser.parse_json(part_result.response_text)
                self._normalize_contexts_for_part(
                    part_payload,
                    contexts,
                    questions,
                    part_result.image_paths,
                )
                result.contexts.extend(contexts)
                result.questions.extend(questions)

            answer_key = self._generate_answer_key(client, model_name)
            result.answer_key.update(answer_key)

        if result.answer_key:
            self.parser.apply_answer_key_to_questions(
                result.questions, result.answer_key
            )

        if not result.contexts and not result.questions and not result.answer_key:
            raise ValueError(
                "No agent output was produced. Select PDFs or answer sheets first."
            )

        duplicates = self.parser.duplicate_question_numbers(result.questions)
        if duplicates:
            duplicate_text = ", ".join(f"Q{number}" for number in duplicates)
            raise ValueError(
                f"Agent output contains duplicate question numbers: {duplicate_text}"
            )

        return result

    def _has_part_input(self, payload: AgentPartPayload) -> bool:
        return bool(
            (payload.part != 2 and payload.question_pdf_path and payload.question_pages)
            or (payload.transcript_pdf_path and payload.transcript_pages)
        )

    def _generate_part(
        self, client, model_name: str, payload: AgentPartPayload, tmp_dir: Path
    ) -> AgentPartResult:
        files = []
        part1_image_paths: list[Path] = []
        prompt_parts = [
            payload.prompt.strip(),
            f"\nTarget TOEIC part: {payload.part}.",
            f"Extract ONLY TOEIC Part {payload.part}.",
            "Return only the raw JSON object with contexts and questions.",
        ]
        if payload.context_text.strip():
            prompt_parts.append(
                f"\nDefault/context text:\n{payload.context_text.strip()}"
            )

        if payload.part == 1 and payload.question_pdf_path and payload.question_pages:
            image_paths = self._prepare_part1_question_images(
                payload.question_pdf_path,
                payload.question_pages,
                tmp_dir / "part_1_question_images",
            )
            part1_image_paths = image_paths
        elif payload.part != 2 and payload.question_pdf_path and payload.question_pages:
            path = self._slice_pdf(
                payload.question_pdf_path,
                payload.question_pages,
                tmp_dir / f"part_{payload.part}_questions.pdf",
            )
            files.append(client.files.upload(file=path))
            prompt_parts.append("\nQuestion pages are attached as a PDF.")

        if payload.transcript_pdf_path and payload.transcript_pages:
            path = self._slice_pdf(
                payload.transcript_pdf_path,
                payload.transcript_pages,
                tmp_dir / f"part_{payload.part}_transcript.pdf",
            )
            files.append(client.files.upload(file=path))
            prompt_parts.append("\nTranscript pages are attached as a PDF.")
            if payload.part in (3, 4):
                prompt_parts.append(
                    "\nUse transcript labels/ranges such as '41-43 refer to...' "
                    "as the grouping key for shared AUDIO_SRT contexts."
                )

        prompt_parts.append(
            f"\nFINAL GUARDRAIL: Output ONLY TOEIC Part {payload.part} data. "
            f"Do not include any other TOEIC part. Return exactly one JSON object "
            f"with top-level arrays named contexts and questions."
        )

        self.progress.emit(f"Sending Part {payload.part} to Gemini...")
        response = client.models.generate_content(
            model=model_name,
            contents=["\n".join(prompt_parts), *files],
        )
        text = self._response_text(response)
        if not text:
            raise ValueError(
                f"Gemini returned an empty response for Part {payload.part}."
            )
        return AgentPartResult(
            response_text=text,
            image_paths=[str(path) for path in part1_image_paths],
        )

    def _prepare_part1_question_images(
        self, pdf_path: str, page_indices: list[int], output_dir: Path
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir = output_dir / "extracted"
        split_dir = output_dir / "split"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        split_dir.mkdir(parents=True, exist_ok=True)

        all_question_images: list[Path] = []
        for page_index in sorted(set(page_indices)):
            self.progress.emit(f"Splitting Part 1 images from page {page_index + 1}...")
            page_sources = self._extract_pdf_page_images(
                pdf_path, page_index, extracted_dir
            )
            page_question_images: list[Path] = []
            for source_path in page_sources:
                page_question_images.extend(
                    self._split_part1_image_file(source_path, split_dir)
                )

            if len(page_question_images) != 2 and len(page_sources) == 2:
                page_question_images = page_sources

            if len(page_question_images) != 2:
                raise ValueError(
                    "Part 1 image split expected exactly 2 images for "
                    f"page {page_index + 1}, but found {len(page_question_images)}."
                )

            all_question_images.extend(page_question_images)

        expected_count = len(set(page_indices)) * 2
        if len(all_question_images) != expected_count:
            raise ValueError(
                "Part 1 image split expected "
                f"{expected_count} image(s), but found {len(all_question_images)}."
            )
        return all_question_images

    def _extract_pdf_page_images(
        self, pdf_path: str, page_index: int, output_dir: Path
    ) -> list[Path]:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required to extract Part 1 images. "
                "Please install requirements.txt."
            ) from exc

        output_paths: list[Path] = []
        with fitz.open(str(pdf_path)) as document:
            if page_index < 0 or page_index >= len(document):
                raise ValueError(
                    f"Page {page_index + 1} is outside {Path(pdf_path).name}."
                )

            page = document[page_index]
            image_list = page.get_images(full=True)
            for image_index, image_info in enumerate(image_list, start=1):
                base_image = document.extract_image(image_info[0])
                image_bytes = base_image["image"]
                image_ext = base_image.get("ext", "png")
                image_path = (
                    output_dir / f"page_{page_index + 1}_img_{image_index}.{image_ext}"
                )
                image_path.write_bytes(image_bytes)
                output_paths.append(image_path)

            if output_paths:
                return output_paths

            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            rendered_path = output_dir / f"page_{page_index + 1}_rendered.png"
            pixmap.save(str(rendered_path))
            return [rendered_path]

    def _split_part1_image_file(self, image_path: Path, output_dir: Path) -> list[Path]:
        try:
            import cv2
        except ImportError as exc:
            raise ImportError(
                "OpenCV is required to split Part 1 images. "
                "Please install requirements.txt."
            ) from exc

        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read extracted image: {image_path.name}")

        h_orig, w_orig, _ = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 230, 255, cv2.THRESH_BINARY_INV)

        margin_w = int(w_orig * 0.05)
        margin_h = int(h_orig * 0.05)
        thresh[0:margin_h, :] = 0
        thresh[h_orig - margin_h : h_orig, :] = 0
        thresh[:, 0:margin_w] = 0
        thresh[:, w_orig - margin_w : w_orig] = 0

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        valid_boxes: list[tuple[int, int, int, int]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            is_large_enough = (w > w_orig * 0.25) and (h > h_orig * 0.18)
            is_not_full_page = (w < w_orig * 0.98) and (h < h_orig * 0.98)
            if is_large_enough and is_not_full_page:
                valid_boxes.append((x, y, w, h))

        if len(valid_boxes) != 2:
            return []

        valid_boxes.sort(key=lambda box: box[1])
        output_paths: list[Path] = []
        for index, (x, y, w, h) in enumerate(valid_boxes, start=1):
            cropped_img = img[y : y + h, x : x + w]
            output_path = output_dir / f"{image_path.stem}_part_{index}.png"
            cv2.imwrite(str(output_path), cropped_img)
            output_paths.append(output_path)
        return output_paths

    def _generate_answer_key(self, client, model_name: str) -> dict[int, str]:
        answer_sheet = self.payload.answer_sheet
        image_paths = [
            path
            for path in (
                answer_sheet.listening_image_path,
                answer_sheet.reading_image_path,
            )
            if path
        ]
        if not image_paths:
            return {}

        self.progress.emit("Sending answer sheet image(s) to Gemini...")
        files = [client.files.upload(file=path) for path in image_paths]
        prompt = answer_sheet.prompt.strip() or self.parser.ANSWER_SHEET_PROMPT_TEXT
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, *files],
        )
        text = self._response_text(response)
        return self.parser.parse_answer_key_csv(text)

    def _slice_pdf(
        self, pdf_path: str, page_indices: list[int], target_path: Path
    ) -> Path:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise ImportError("pypdf is required for PDF page extraction.") from exc

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        page_count = len(reader.pages)
        for page_index in sorted(set(page_indices)):
            if page_index < 0 or page_index >= page_count:
                raise ValueError(
                    f"Page {page_index + 1} is outside {Path(pdf_path).name}."
                )
            writer.add_page(reader.pages[page_index])
        with target_path.open("wb") as handle:
            writer.write(handle)
        return target_path

    def _normalize_contexts_for_part(
        self,
        payload: AgentPartPayload,
        contexts: list[dict],
        questions: list[dict],
        part1_image_paths: list[str] | None = None,
    ) -> None:
        id_map: dict[str, str] = {}
        context_image_map = self._part1_context_image_map(
            contexts, questions, part1_image_paths or []
        )
        for index, context in enumerate(contexts):
            old_id = str(context.get("llm_id") or f"ctx_{index}")
            new_id = f"part{payload.part}_{old_id}"
            id_map[old_id] = new_id
            context["llm_id"] = new_id
            context["part"] = int(context.get("part") or payload.part)
            if payload.part == 1:
                context["context_type"] = "IMAGE_DIAGRAM"
                content = context.get("content")
                if not isinstance(content, dict):
                    content = {"text": str(content or "")}
                content.setdefault("text", "")
                image_path = context_image_map.get(old_id)
                if image_path:
                    content["_source_image_path"] = image_path
                    content["image_filename"] = Path(image_path).name
                context["content"] = content
            elif payload.part == 2:
                context["context_type"] = "STANDALONE"
                context["content"] = {"text": payload.context_text.strip()}

        for question in questions:
            old_ref = str(question.get("llm_context_id") or "")
            if old_ref in id_map:
                question["llm_context_id"] = id_map[old_ref]
            if payload.part == 1:
                question["question_type"] = "MULTIPLE_CHOICE"
                question["content"] = (
                    "Look at the picture and choose the statement that best describes it."
                )

        if payload.part == 1:
            self._renumber_part1_questions(questions)

    def _renumber_part1_questions(self, questions: list[dict]) -> None:
        sorted_questions = sorted(
            questions,
            key=lambda question: int(question.get("question_number", 0) or 0),
        )
        numbers = [
            int(question.get("question_number", 0) or 0)
            for question in sorted_questions
        ]
        if numbers and min(numbers) == 1 and max(numbers) <= len(numbers):
            return

        for index, question in enumerate(sorted_questions, start=1):
            question["question_number"] = index

    def _part1_context_image_map(
        self, contexts: list[dict], questions: list[dict], image_paths: list[str]
    ) -> dict[str, str]:
        if not image_paths:
            return {}

        context_order = [
            str(context.get("llm_id") or f"ctx_{index}")
            for index, context in enumerate(contexts)
        ]
        if len(context_order) == len(image_paths):
            return dict(zip(context_order, image_paths))

        sorted_questions = sorted(
            questions,
            key=lambda question: int(question.get("question_number", 0) or 0),
        )
        mapped: dict[str, str] = {}
        for image_path, question in zip(image_paths, sorted_questions):
            llm_context_id = str(question.get("llm_context_id") or "")
            if llm_context_id and llm_context_id not in mapped:
                mapped[llm_context_id] = image_path

        if mapped:
            return mapped

        return {
            context_id: image_paths[index]
            for index, context_id in enumerate(context_order[: len(image_paths)])
        }

    def _response_text(self, response) -> str:
        text = getattr(response, "text", "")
        if text:
            return str(text).strip()
        candidates = getattr(response, "candidates", None) or []
        chunks: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    chunks.append(str(part_text))
        return "\n".join(chunks).strip()


class ImportQuestionsAgentViewModel(QObject):
    state_changed = Signal()
    progress_message = Signal(str)
    error_message = Signal(str)
    import_ready = Signal()

    DEFAULT_PART2_CONTEXT = "Mark your answer on your answer sheet"
    PART_PROMPTS = {
        1: """
Analyze ONLY TOEIC Listening Part 1 (Photographs).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.

The attached images are Part 1 photograph question images. Each image is one question.
Do NOT infer or create Part 2, Part 3, or Part 4 questions.
Use question numbers in the order images are attached, starting from 1 unless a printed number is visible.

Return this schema:
{
  "contexts": [
    {
      "id": "p1_q1",
      "part": 1,
      "context_type": "IMAGE_DIAGRAM",
      "content": {"text": "Brief description of the photograph."},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": "Vietnamese translation/description of the photograph."}
    }
  ],
  "questions": [
    {
      "context_id": "p1_q1",
      "question_number": 1,
      "question_type": "MULTIPLE_CHOICE",
      "content": "Look at the picture and choose the statement that best describes it.",
      "options": ["", "", "", ""],
      "correct_answer": "",
      "additional_meta": {"note": "Leave empty unless an answer/explanation is visible."}
    }
  ]
}

STRICT PART 1 RULES:
1. Every context_type must be IMAGE_DIAGRAM.
2. Create exactly one context and one question for each attached photograph image.
3. Every question must reference its own context_id.
4. Do not use question numbers 11, 12, 13, 14 unless those exact numbers are visibly printed on the image.
5. Do not create spoken question-response content. That belongs to Part 2, not Part 1.
""".strip(),
        2: """
Analyze ONLY TOEIC Listening Part 2 (Question-Response).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.

The attached transcript pages are Part 2 audio transcript pages. The fixed context text is provided separately.
Do NOT infer or create Part 1 photograph, Part 3 conversation, or Part 4 talk questions.

Return this schema:
{
  "contexts": [
    {
      "id": "p2_q11",
      "part": 2,
      "context_type": "STANDALONE",
      "content": {"text": "Mark your answer on your answer sheet"},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": ""}
    }
  ],
  "questions": [
    {
      "context_id": "p2_q11",
      "question_number": 11,
      "question_type": "MULTIPLE_CHOICE",
      "content": "Spoken question or statement.",
      "options": ["Response A", "Response B", "Response C"],
      "correct_answer": "",
      "additional_meta": {"note": "Vietnamese translation and explanation if available."}
    }
  ]
}

STRICT PART 2 RULES:
1. Every context_type must be STANDALONE.
2. Every Part 2 question must have its own dedicated context.
3. Extract only Part 2 question-response items.
4. Options must contain exactly 3 responses A, B, C.
""".strip(),
        3: """
Analyze ONLY TOEIC Listening Part 3 (Conversations).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.

The attached pages contain Part 3 question pages and/or transcript pages.
Do NOT infer or create Part 1, Part 2, or Part 4 questions.

Transcript grouping labels are authoritative. In transcript pages, labels such as
"41-43 refer to the following conversation" or "Questions 41-43 refer to..."
mean that questions 41, 42, and 43 must share exactly one AUDIO_SRT context.
Use the full transcript text following that label as that context's content.text.
Create a new context when the next start-number/range label appears.

Return this schema:
{
  "contexts": [
    {
      "id": "p3_41_43",
      "part": 3,
      "context_type": "AUDIO_SRT",
      "content": {"text": "Full conversation transcript for questions 41-43."},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": "Vietnamese translation/summary of the conversation."}
    }
  ],
  "questions": [
    {
      "context_id": "p3_41_43",
      "question_number": 41,
      "question_type": "MULTIPLE_CHOICE",
      "content": "Printed Part 3 question stem.",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "",
      "additional_meta": {"note": "Vietnamese translation and explanation if available."}
    }
  ]
}

STRICT PART 3 RULES:
1. Every context part must be 3.
2. Every context_type must be AUDIO_SRT.
3. Questions sharing one conversation must reference the same context_id.
4. Extract only Part 3 conversation questions.
5. Preserve printed question numbers when visible.
6. Use transcript start-number/range labels to group questions; do not split questions from one label into separate contexts.
7. If a label says 41-43, only questions 41, 42, and 43 may reference that context.
8. The top-level JSON object must contain exactly "contexts" and "questions" arrays.
9. Do not return nested groups, markdown tables, CSV, or any schema other than the JSON object above.
""".strip(),
        4: """
Analyze ONLY TOEIC Listening Part 4 (Talks).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.

The attached pages contain Part 4 question pages and/or transcript pages.
Do NOT infer or create Part 1, Part 2, or Part 3 questions.

Transcript grouping labels are authoritative. In transcript pages, labels such as
"71-73 refer to the following talk" or "Questions 71-73 refer to..."
mean that questions 71, 72, and 73 must share exactly one AUDIO_SRT context.
Use the full transcript text following that label as that context's content.text.
Create a new context when the next start-number/range label appears.

Return this schema:
{
  "contexts": [
    {
      "id": "p4_71_73",
      "part": 4,
      "context_type": "AUDIO_SRT",
      "content": {"text": "Full talk transcript for questions 71-73."},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": "Vietnamese translation/summary of the talk."}
    }
  ],
  "questions": [
    {
      "context_id": "p4_71_73",
      "question_number": 71,
      "question_type": "MULTIPLE_CHOICE",
      "content": "Printed Part 4 question stem.",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "",
      "additional_meta": {"note": "Vietnamese translation and explanation if available."}
    }
  ]
}

STRICT PART 4 RULES:
1. Every context part must be 4.
2. Every context_type must be AUDIO_SRT.
3. Questions sharing one talk must reference the same context_id.
4. Extract only Part 4 talk questions.
5. Preserve printed question numbers when visible.
6. Use transcript start-number/range labels to group questions; do not split questions from one label into separate contexts.
7. If a label says 71-73, only questions 71, 72, and 73 may reference that context.
8. The top-level JSON object must contain exactly "contexts" and "questions" arrays.
9. Do not return nested groups, markdown tables, CSV, or any schema other than the JSON object above.
""".strip(),
    }

    def __init__(self, parser: ImportQuestionsViewModel | None = None, parent=None):
        super().__init__(parent)
        self.parser = parser or ImportQuestionsViewModel(self)
        self.part_payloads: dict[int, AgentPartPayload] = {
            part: AgentPartPayload(part=part, prompt=self._default_part_prompt(part))
            for part in range(1, 5)
        }
        self.part_payloads[2].context_text = self.DEFAULT_PART2_CONTEXT
        self.answer_sheet = AgentAnswerSheetPayload(
            prompt=self.parser.ANSWER_SHEET_PROMPT_TEXT
        )
        self.result_contexts: list[dict] = []
        self.result_questions: list[dict] = []
        self.result_answer_key: dict[int, str] = {}
        self.is_loading = False
        self._worker: ImportQuestionsAgentWorker | None = None

    def _default_part_prompt(self, part: int) -> str:
        return self.PART_PROMPTS.get(part, self.parser.READING_PROMPT_TEXT)

    def set_part_pdf(
        self, part: int, lane: str, pdf_path: str, page_indices: list[int]
    ) -> None:
        payload = self.part_payloads[part]
        if lane == "questions":
            if part == 2:
                payload.question_pdf_path = ""
                payload.question_pages = []
                self.state_changed.emit()
                return
            payload.question_pdf_path = pdf_path
            payload.question_pages = list(page_indices)
        elif lane == "transcripts":
            payload.transcript_pdf_path = pdf_path
            payload.transcript_pages = list(page_indices)
        else:
            raise ValueError(f"Unknown PDF lane: {lane}")
        self.state_changed.emit()

    def set_part_prompt(self, part: int, prompt: str) -> None:
        self.part_payloads[part].prompt = prompt

    def set_part_context_text(self, part: int, text: str) -> None:
        self.part_payloads[part].context_text = text

    def set_answer_sheet_image(self, lane: str, image_path: str) -> None:
        if lane == "listening":
            self.answer_sheet.listening_image_path = image_path
        elif lane == "reading":
            self.answer_sheet.reading_image_path = image_path
        else:
            raise ValueError(f"Unknown answer sheet lane: {lane}")
        self.state_changed.emit()

    def set_answer_sheet_prompt(self, prompt: str) -> None:
        self.answer_sheet.prompt = prompt

    def pdf_summary(self, part: int, lane: str) -> str:
        payload = self.part_payloads[part]
        if lane == "questions":
            return self._format_pdf_summary(
                payload.question_pdf_path, payload.question_pages
            )
        return self._format_pdf_summary(
            payload.transcript_pdf_path, payload.transcript_pages
        )

    def _format_pdf_summary(self, pdf_path: str, page_indices: list[int]) -> str:
        if not pdf_path:
            return "No PDF selected"
        pages = ", ".join(str(index + 1) for index in page_indices) or "none"
        return f"{Path(pdf_path).name}: pages {pages}"

    def can_send(self) -> bool:
        if self.is_loading:
            return False
        return any(
            (payload.part != 2 and payload.question_pages) or payload.transcript_pages
            for payload in self.part_payloads.values()
        ) or bool(
            self.answer_sheet.listening_image_path
            or self.answer_sheet.reading_image_path
        )

    def send_to_agent(self) -> None:
        if self.is_loading:
            return
        if not self.can_send():
            self.error_message.emit("Select PDF pages or answer sheet images first.")
            return

        payload = AgentImportPayload(
            parts=[
                payload.model_copy(
                    update={"prompt": self._effective_part_prompt(part, payload.prompt)}
                )
                for part, payload in self.part_payloads.items()
            ],
            answer_sheet=self.answer_sheet,
        )
        self.is_loading = True
        self.state_changed.emit()

        self._worker = ImportQuestionsAgentWorker(payload, self.parser)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.run()

    def _on_finished(self, result: dict) -> None:
        self.is_loading = False
        self.result_contexts = list(result.get("contexts", []))
        self.result_questions = list(result.get("questions", []))
        raw_answer_key = result.get("answer_key", {}) or {}
        self.result_answer_key = {
            int(key): str(value) for key, value in raw_answer_key.items()
        }
        self.state_changed.emit()
        self.import_ready.emit()

    def _on_error(self, message: str) -> None:
        self.is_loading = False
        self.error_message.emit(message)
        self.state_changed.emit()

    def run_with_manual_provider(
        self, provider: Callable[[AgentImportPayload], AgentImportResult]
    ) -> None:
        payload = AgentImportPayload(
            parts=[
                payload.model_copy(
                    update={"prompt": self._effective_part_prompt(part, payload.prompt)}
                )
                for part, payload in self.part_payloads.items()
            ],
            answer_sheet=self.answer_sheet,
        )
        result = provider(payload)
        self.result_contexts = result.contexts
        self.result_questions = result.questions
        self.result_answer_key = result.answer_key
        self.import_ready.emit()

    def _effective_part_prompt(self, part: int, user_prompt: str) -> str:
        base_prompt = self._default_part_prompt(part)
        user_prompt = user_prompt.strip()
        if not user_prompt or user_prompt == base_prompt:
            return base_prompt
        return (
            f"{base_prompt}\n\nUSER ADDITIONAL INSTRUCTIONS FOR PART {part} ONLY:\n"
            f"{user_prompt}\n\n"
            f"These additional instructions must not override the requirement to "
            f"extract ONLY TOEIC Part {part}."
        )
