from __future__ import annotations

import ast
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from google.genai import Client, types
from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, QThread, Signal
from src.models.exam import ImportAgentTask, ToeicPartResponseSchema
from src.repositories.sqlite.import_agent_task_repo import ImportAgentTaskRepository
from src.utils.helpers import get_local_media_dir
from src.viewmodels.import_questions_viewmodel import ImportQuestionsViewModel

load_dotenv()


class AgentPartPayload(BaseModel):
    part: int
    question_pdf_path: str = ""
    question_pages: list[int] = Field(default_factory=list[int])
    transcript_pdf_path: str = ""
    transcript_pages: list[int] = Field(default_factory=list[int])
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
    finished = Signal(str, dict)
    error = Signal(str, str)

    def __init__(
        self,
        task_id: str,
        parser: ImportQuestionsViewModel,
        task_repo: ImportAgentTaskRepository | None = None,
    ):
        super().__init__()
        self.task_id = task_id
        self.parser = parser
        self.task_repo = task_repo or ImportAgentTaskRepository()
        self.payload = AgentImportPayload()

    def run(self):
        try:
            task = self.task_repo.mark_running(self.task_id)
            if task is None:
                raise ValueError("The import agent request no longer exists.")
            self.payload = AgentImportPayload.model_validate(task.payload)
            result = self._run_agent()
            result_data = result.model_dump()
            self.task_repo.mark_succeeded(self.task_id, result_data)
            self.finished.emit(self.task_id, result_data)
        except Exception as exc:
            message = str(exc)
            self.task_repo.mark_failed(
                self.task_id,
                message,
                retryable=self._is_retryable_error(message),
            )
            self.error.emit(self.task_id, message)

    def _is_retryable_error(self, message: str) -> bool:
        normalized = message.upper()
        return any(
            token in normalized
            for token in ("503", "UNAVAILABLE", "SERVICE BUSY", "HIGH DEMAND")
        )

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
                contexts, questions = self._parse_agent_response(
                    part_result.response_text
                )
                self._normalize_contexts_for_part(
                    part_payload,
                    contexts,
                    questions,
                    part_result.image_paths,
                )
                result.contexts.extend(contexts)
                result.questions.extend(questions)

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

    def _parse_agent_response(
        self, response_text: str
    ) -> tuple[list[dict], list[dict]]:
        data = self._load_agent_response_object(response_text)
        contexts: list[dict] = []
        questions: list[dict] = []
        for index, raw_context in enumerate(data.get("contexts", []) or []):
            if not isinstance(raw_context, dict):
                continue
            llm_id = str(raw_context.get("id") or f"ctx_{index}").strip()
            if not llm_id:
                llm_id = f"ctx_{index}"
            content = raw_context.get("content") or {}
            if not isinstance(content, dict):
                content = {"text": str(content)}
            meta = raw_context.get("additional_meta") or {}
            if not isinstance(meta, dict):
                meta = {}
            contexts.append(
                {
                    "llm_id": llm_id,
                    "part": int(raw_context.get("part") or 1),
                    "context_type": str(
                        raw_context.get("context_type") or "STANDALONE"
                    ).upper(),
                    "content": content,
                    "index": int(raw_context.get("index") or index),
                    "additional_meta": {
                        "audio_start": float(meta.get("audio_start") or 0.0),
                        "audio_end": float(meta.get("audio_end") or 0.0),
                        "note": str(meta.get("note") or ""),
                    },
                    "user_id": str(raw_context.get("user_id")),
                }
            )
            for raw_question in raw_context.get("questions", []) or []:
                if isinstance(raw_question, dict):
                    questions.append(self._map_agent_question(raw_question, llm_id))

        for raw_question in data.get("questions", []) or []:
            if isinstance(raw_question, dict):
                questions.append(self._map_agent_question(raw_question, ""))
        return contexts, questions

    def _load_agent_response_object(self, response_text: str) -> dict:
        text = response_text.strip()
        if text and text[0] == text[-1] and text[0] in {"'", '"'}:
            try:
                unwrapped = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                unwrapped = text
            if isinstance(unwrapped, str):
                text = unwrapped.strip()
        data = json.loads(text)
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise ValueError("Agent response must be a JSON object.")
        return data

    def _map_agent_question(self, raw_question: dict, parent_context_id: str) -> dict:
        options = raw_question.get("options") or []
        if isinstance(options, str):
            options = [
                option.strip() for option in options.split(",") if option.strip()
            ]
        if not isinstance(options, list):
            options = []
        meta = raw_question.get("additional_meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        llm_context_id = str(raw_question.get("context_id") or "").strip()
        return {
            "llm_context_id": llm_context_id or parent_context_id,
            "content": str(raw_question.get("content") or "").strip(),
            "options": json.dumps(
                [str(option) for option in options], ensure_ascii=False
            ),
            "correct_answer": str(raw_question.get("correct_answer") or "")
            .strip()
            .upper(),
            "question_number": int(raw_question.get("question_number") or 0),
            "question_type": str(
                raw_question.get("question_type") or "MULTIPLE_CHOICE"
            ).upper(),
            "additional_meta": {"note": str(meta.get("note") or "")},
            "user_id": str(raw_question.get("user_id")),
        }

    def _generate_part(
        self, client: Client, model_name: str, payload: AgentPartPayload, tmp_dir: Path
    ) -> AgentPartResult:
        files = []
        part1_image_paths: list[Path] = []
        prompt_parts = [
            payload.prompt.strip(),
            f"\nTarget TOEIC part: {payload.part}.",
            f"Extract ONLY TOEIC Part {payload.part}.",
            "Return only the raw JSON object with contexts containing nested questions.",
            self._vietnamese_note_contract(),
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
            prompt_parts.append(
                "\nPart 1 photograph images were split locally for saving only; "
                "they are not attached to this agent request."
            )
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

        answer_sheet_path = self._answer_sheet_path_for_part(payload.part)
        if answer_sheet_path:
            files.append(client.files.upload(file=answer_sheet_path))
            prompt_parts.append(
                "\nAnswer sheet image is attached. Use it to set correct_answer "
                "for this part and to support the Vietnamese explanation notes."
            )

        prompt_parts.append(
            f"\nFINAL GUARDRAIL: Output ONLY TOEIC Part {payload.part} data. "
            f"Do not include any other TOEIC part. Return exactly one JSON object "
            f"with a top-level contexts array. Put each context's questions inside "
            f"that context's nested questions array."
        )

        self.progress.emit(f"Sending Part {payload.part} to Gemini...")
        print(f"len(files)={len(files)}")
        response = client.models.generate_content(
            model=model_name,
            contents=["\n".join(prompt_parts), *files],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ToeicPartResponseSchema,
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        dump_path = self._save_agent_response_file(response, f"part_{payload.part}")
        self.progress.emit(f"Saved agent response: {dump_path}")
        text = self._response_text(response)
        if not text:
            raise ValueError(
                f"Gemini returned an empty response for Part {payload.part}."
            )
        return AgentPartResult(
            response_text=text,
            image_paths=[str(path) for path in part1_image_paths],
        )

    def _vietnamese_note_contract(self) -> str:
        target_lang = getattr(self.parser, "TARGET_LANG", "Vietnamese (vn)")
        return f"""
VIETNAMESE NOTE CONTRACT:
TRANSLATION TARGET LANGUAGE: {target_lang}
1. Every contexts[].additional_meta.note and questions[].additional_meta.note value must be natural Vietnamese text, never English-only placeholder text.
2. For STANDALONE contexts, contexts[].additional_meta.note must be an empty string.
3. For AUDIO_SRT, READING_PASSAGE, and IMAGE_DIAGRAM contexts, contexts[].additional_meta.note must contain the Vietnamese translation or Vietnamese summary of contexts[].content.text.
4. Every question note is REQUIRED and must be non-empty. Do not use "if available", "leave empty", or similar conditional wording.
5. Format questions[].additional_meta.note exactly like this, with one translated line per source line and one blank line before the explanation:
[Vietnamese translation of the question stem, unless the stem is exactly "-------"]
[Vietnamese translation of option A]
[Vietnamese translation of option B]
[Vietnamese translation of option C]
[Vietnamese translation of option D, if present]

[Detailed Vietnamese grammar/context explanation explaining why correct_answer is right, using transcript/passage keywords.]
6. If correct_answer is empty because no answer key is visible, still provide Vietnamese translations and explain what evidence is visible; do not leave the note empty.
""".strip()

    def _answer_sheet_path_for_part(self, part: int) -> str:
        answer_sheet = self.payload.answer_sheet
        if part in (1, 2, 3, 4):
            return answer_sheet.listening_image_path
        return answer_sheet.reading_image_path

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
                    self._override_context_image(content, image_path)
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
            self._append_missing_part1_image_contexts(
                contexts,
                questions,
                part1_image_paths or [],
                set(context_image_map.values()),
            )
            self._renumber_part1_questions(questions)

    def _override_context_image(self, content: dict, image_path: str) -> None:
        image_filename = Path(image_path).name
        content["_source_image_path"] = image_path
        content["image_path"] = image_path
        content["image_filename"] = image_filename

    def _append_missing_part1_image_contexts(
        self,
        contexts: list[dict],
        questions: list[dict],
        image_paths: list[str],
        used_image_paths: set[str],
    ) -> None:
        if not image_paths:
            return

        next_context_index = len(contexts)
        next_question_number = self._next_question_number(questions)
        for image_path in image_paths:
            if image_path in used_image_paths:
                continue

            context_id = f"part1_local_image_{next_context_index + 1}"
            content = {"text": Path(image_path).stem}
            self._override_context_image(content, image_path)
            contexts.append(
                {
                    "llm_id": context_id,
                    "part": 1,
                    "context_type": "IMAGE_DIAGRAM",
                    "content": content,
                    "index": next_context_index,
                    "additional_meta": {
                        "audio_start": 0.0,
                        "audio_end": 0.0,
                        "note": "",
                    },
                    "user_id": "None",
                }
            )
            questions.append(
                {
                    "llm_context_id": context_id,
                    "content": (
                        "Look at the picture and choose the statement that best describes it."
                    ),
                    "options": json.dumps(["", "", "", ""], ensure_ascii=False),
                    "correct_answer": "",
                    "question_number": next_question_number,
                    "question_type": "MULTIPLE_CHOICE",
                    "additional_meta": {"note": ""},
                    "user_id": "None",
                }
            )
            used_image_paths.add(image_path)
            next_context_index += 1
            next_question_number += 1

    def _next_question_number(self, questions: list[dict]) -> int:
        numbers: list[int] = []
        for question in questions:
            try:
                number = int(question.get("question_number", 0) or 0)
            except (TypeError, ValueError):
                number = 0
            if number > 0:
                numbers.append(number)
        return (max(numbers) + 1) if numbers else 1

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
        text = self._response_text_from_parts(response)
        if text:
            return text
        text = getattr(response, "text", "")
        if text:
            return str(text).strip()
        return ""

    def _response_text_from_parts(self, response) -> str:
        candidates = getattr(response, "candidates", None) or []
        chunks: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    chunks.append(str(part_text))
        return "\n".join(chunks).strip()

    def _save_agent_response_file(self, response, label: str) -> str:
        response_dir = self._agent_response_dir()
        response_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_task_id = "".join(
            char if char.isalnum() or char in "-_" else "_" for char in self.task_id
        )
        safe_label = "".join(
            char if char.isalnum() or char in "-_" else "_" for char in label
        )
        path = response_dir / f"{timestamp}_{safe_task_id}_{safe_label}.json"
        payload = {
            "task_id": self.task_id,
            "label": label,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "response_text": self._response_text_from_parts(response),
            "candidates": self._dump_response_candidates(response),
            "response": self._json_safe(response),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(path)

    def _agent_response_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".codex" / "import_agent_responses"

    def _dump_response_candidates(self, response) -> list[dict]:
        candidates = getattr(response, "candidates", None) or []
        dumped_candidates: list[dict] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            dumped_parts = [
                self._dump_response_part(part)
                for part in getattr(content, "parts", []) or []
            ]
            dumped_candidates.append(
                {
                    "finish_reason": self._json_safe(
                        getattr(candidate, "finish_reason", None)
                    ),
                    "content_role": getattr(content, "role", None),
                    "parts": dumped_parts,
                }
            )
        return dumped_candidates

    def _dump_response_part(self, part) -> dict:
        fields = (
            "text",
            "thought",
            "thought_signature",
            "inline_data",
            "file_data",
            "function_call",
            "function_response",
            "executable_code",
            "code_execution_result",
        )
        return {
            field: self._json_safe(getattr(part, field))
            for field in fields
            if hasattr(part, field) and getattr(part, field) is not None
        }

    def _json_safe(self, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.hex()
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, BaseModel):
            return self._json_safe(value.model_dump())
        if hasattr(value, "model_dump"):
            return self._json_safe(value.model_dump())
        if hasattr(value, "to_json_dict"):
            return self._json_safe(value.to_json_dict())
        return repr(value)


class ImportQuestionsAgentViewModel(QObject):
    state_changed = Signal()
    tasks_changed = Signal()
    progress_message = Signal(str)
    error_message = Signal(str)
    import_ready = Signal()
    TARGET_LANG = "Vietnamese (vn)"

    TOEIC_PARTS = range(1, 8)
    DEFAULT_PART2_CONTEXT = "Mark your answer on your answer sheet"
    PART_PROMPTS = {
        1: """
Analyze ONLY TOEIC Listening Part 1 (Photographs).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

The attached transcript pages are TOEIC Part 1 audio transcript pages.
Do NOT infer or create Part 2, Part 3, or Part 4 questions.
Use question numbers in transcript order, starting from 1 unless printed/spoken numbers are visible.

Return this schema:
{
  "contexts": [
    {
      "id": "p1_q1",
      "part": 1,
      "context_type": "IMAGE_DIAGRAM",
      "content": {"text": ""},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
      "questions": [
        {
          "question_number": 1,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Look at the picture and choose the statement that best describes it.",
          "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
          "correct_answer": "Required get from answer sheet image",
          "additional_meta": {
              "note": "REQUIRED. Strictly format this field exactly as follows:\n[Translation of the question content stem into {TARGET_LANG}]\n[Translation of option 1 into {TARGET_LANG}]\n[Translation of option 2 into {TARGET_LANG}]\n[Translation of option 3 into {TARGET_LANG}]\n[Translation of option 4 into {TARGET_LANG} (if applicable)]\n\n[Detailed grammatical/contextual explanation in {TARGET_LANG} explaining why the correct_answer is right based on keywords from the transcript.]"
          }
        }
      ]
    }
  ]
}

STRICT PART 1 RULES:
1. Every context_type must be IMAGE_DIAGRAM.
2. Create exactly one context and one question for each attached photograph image.
3. every questions options must be as flat string array. Stripped of prefixes like (A), B., C), etc. Keep original order.
4. Do not use question numbers 11, 12, 13, 14 unless those exact numbers are visibly printed on the image.
5. Do not create spoken question-response content. That belongs to Part 2, not Part 1.
6. Only take questions from 1 to 10.
""".replace("{TARGET_LANG}", TARGET_LANG),
        2: """
Analyze ONLY TOEIC Listening Part 2 (Question-Response).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

The attached transcript pages are Part 2 audio transcript pages. The fixed context text is provided separately.

Return this schema:
{
  "contexts": [
    {
      "id": "p2_q11",
      "part": 2,
      "context_type": "STANDALONE",
      "content": {"text": "Mark your answer on your answer sheet"},
      "index": 0,
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
      "questions": [
        {
          "question_number": 11,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Spoken question or statement.",
          "options": ["Response A", "Response B", "Response C"],
          "correct_answer": "Required get from answer sheet image",
          "additional_meta": {
              "note": "REQUIRED. Strictly format this field exactly as follows:\n[Translation of the question content stem into {TARGET_LANG}]\n[Translation of option 1 into {TARGET_LANG}]\n[Translation of option 2 into {TARGET_LANG}]\n[Translation of option 3 into {TARGET_LANG}]\n[Translation of option 4 into {TARGET_LANG} (if applicable)]\n\n[Detailed grammatical/contextual explanation in {TARGET_LANG} explaining why the correct_answer is right based on keywords from the transcript.]"
          }
        }
      ]
    }
  ]
}

STRICT PART 2 RULES:
1. Every context_type must be STANDALONE and 1 context only has 1 question.
2. questions.content: Put the spoken Question/Statement here (e.g., "Where is the meeting room?").
3. questions.options: Put the 3 spoken response choices (A, B, C) here,Stripped of prefixes like (A), B., C) and keep original order.
4. Never leave questions.additional_meta.note empty, even when correct_answer is unknown.
5. only take all questions from 11 to 40.
""".replace("{TARGET_LANG}", TARGET_LANG),
        3: """
Analyze ONLY TOEIC Listening Part 3 (Conversations).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

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
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": "REQUIRED. Vietnamese translation of the conversation."},
      "questions": [
        {
          "question_number": 41,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Printed Part 3 question stem.",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "",
          "additional_meta": {"note": "REQUIRED. Vietnamese translation of the question stem, Vietnamese translation of options A-D, blank line, then Vietnamese explanation using conversation keywords."}
        },
        {
          "question_number": 42,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Printed Part 3 question stem.",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "",
          "additional_meta": {"note": "REQUIRED. Vietnamese translation of the question stem, Vietnamese translation of options A-D, blank line, then Vietnamese explanation using conversation keywords."}
        }
      ]
    }
  ]
}

STRICT PART 3 RULES:
1. Every context part must be 3.
2. Every context_type must be AUDIO_SRT.
3. Only take all questions from 41 to 70.
4. Questions sharing one conversation must be nested in the same context's questions array.
5. Extract only Part 3 conversation questions.
6. Preserve printed question numbers when visible.
7. Use transcript start-number/range labels to group questions; do not split questions from one label into separate contexts.
8. If a label says 41-43, only questions 41, 42, and 43 may reference that context.
9. The top-level JSON object must contain exactly one "contexts" array; do not add a top-level "questions" array.
10. Do not return nested groups, markdown tables, CSV, or any schema other than the JSON object above.
11. Never leave contexts.additional_meta.note or questions.additional_meta.note empty.
""".replace("{TARGET_LANG}", TARGET_LANG),
        4: """
Analyze ONLY TOEIC Listening Part 4 (Talks).
OUTPUT CONSTRAINT: Output ONLY one raw JSON object. No markdown, no code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

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
      "additional_meta": {"audio_start": 0.0, "audio_end": 0.0, "note": "REQUIRED. Vietnamese translation."},
      "questions": [
        {
          "question_number": 71,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Printed Part 4 question stem.",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "",
          "additional_meta": {"note": "REQUIRED. Vietnamese translation of the question stem, Vietnamese translation of options A-D, blank line, then Vietnamese explanation using talk keywords."}
        },
        {
          "question_number": 72,
          "question_type": "MULTIPLE_CHOICE",
          "content": "Printed Part 4 question stem.",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "",
          "additional_meta": {"note": "REQUIRED. Vietnamese translation of the question stem, Vietnamese translation of options A-D, blank line, then Vietnamese explanation using talk keywords."}
        }
      ]
    }
  ]
}

STRICT PART 4 RULES:
1. Every context part must be 4.
2. Every context_type must be AUDIO_SRT.
3. Only take all questions from 71 to 100.
4. Questions sharing one talk must be nested in the same context's questions array.
5. Extract only Part 4 talk questions.
6. Preserve printed question numbers when visible.
7. Use transcript start-number/range labels to group questions; do not split questions from one label into separate contexts.
8. If a label says 71-73, only questions 71, 72, and 73 may reference that context.
9. The top-level JSON object must contain exactly one "contexts" array; do not add a top-level "questions" array.
10. Do not return nested groups, markdown tables, CSV, or any schema other than the JSON object above.
11. Never leave contexts.additional_meta.note or questions.additional_meta.note empty.
""".replace("{TARGET_LANG}", TARGET_LANG),
    }

    def __init__(
        self,
        parser: ImportQuestionsViewModel | None = None,
        task_repo: ImportAgentTaskRepository | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.parser = parser or ImportQuestionsViewModel(self)
        self.task_repo = task_repo or ImportAgentTaskRepository()
        self.part_payloads: dict[int, AgentPartPayload] = {
            part: AgentPartPayload(part=part, prompt=self._default_part_prompt(part))
            for part in self.TOEIC_PARTS
        }
        self.part_payloads[2].context_text = self.DEFAULT_PART2_CONTEXT
        self.answer_sheet = AgentAnswerSheetPayload(
            prompt=self.parser.ANSWER_SHEET_PROMPT_TEXT
        )
        self.result_contexts: list[dict] = []
        self.result_questions: list[dict] = []
        self.result_answer_key: dict[int, str] = {}
        self.is_loading = False
        self.current_task_id: str | None = None
        self._worker: ImportQuestionsAgentWorker | None = None
        self._batch_task_ids: list[str] = []
        self._batch_results: dict[str, dict] = {}

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
        if not self._parts_with_input():
            return False
        return not self._missing_required_answer_sheets()

    def send_to_agent(self) -> None:
        if self.is_loading:
            return
        if not self._parts_with_input():
            self.error_message.emit("Select PDF pages first.")
            return

        missing_sheets = self._missing_required_answer_sheets()
        if missing_sheets:
            self.error_message.emit(
                "Select required answer sheet image(s): "
                + ", ".join(missing_sheets)
                + "."
            )
            return

        tasks = self.create_agent_tasks()
        if not tasks:
            self.error_message.emit("No agent requests were created.")
            return
        self.result_contexts = []
        self.result_questions = []
        self.result_answer_key = {}
        self._batch_task_ids = [task.id for task in tasks]
        self._batch_results = {}
        self._start_task(tasks[0].id)

    def create_agent_task(self) -> ImportAgentTask:
        payload = self._build_agent_payload()
        task = self.task_repo.create_task(payload.model_dump())
        self.tasks_changed.emit()
        return task

    def create_agent_tasks(self) -> list[ImportAgentTask]:
        payloads = self._build_agent_request_payloads()
        tasks = [
            self.task_repo.create_task(payload.model_dump()) for payload in payloads
        ]
        self.tasks_changed.emit()
        return tasks

    def _build_agent_payload(self) -> AgentImportPayload:
        return AgentImportPayload(
            parts=[
                payload.model_copy(
                    update={"prompt": self._effective_part_prompt(part, payload.prompt)}
                )
                for part, payload in self.part_payloads.items()
            ],
            answer_sheet=self.answer_sheet,
        )

    def _build_agent_request_payloads(self) -> list[AgentImportPayload]:
        selected_parts = set(self._parts_with_input())
        payloads: list[AgentImportPayload] = []
        for part in self.TOEIC_PARTS:
            if part not in selected_parts:
                continue
            payloads.append(self._payload_for_parts([part]))
        return payloads

    def _payload_for_parts(self, parts: list[int]) -> AgentImportPayload:
        return AgentImportPayload(
            parts=[
                self.part_payloads[part].model_copy(
                    update={
                        "prompt": self._effective_part_prompt(
                            part, self.part_payloads[part].prompt
                        )
                    }
                )
                for part in parts
            ],
            answer_sheet=self.answer_sheet,
        )

    def _start_task(self, task_id: str) -> bool:
        if self.is_loading:
            return False
        self.is_loading = True
        self.current_task_id = task_id
        self.state_changed.emit()
        self.tasks_changed.emit()

        self._worker = ImportQuestionsAgentWorker(task_id, self.parser, self.task_repo)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        return True

    def _on_finished(self, task_id: str, result: dict) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.current_task_id = None
        self._batch_results[task_id] = result
        self._merge_batch_results()
        self.state_changed.emit()
        self.tasks_changed.emit()
        if self._start_next_batch_task(after_task_id=task_id):
            return
        self.import_ready.emit()

    def _on_error(self, task_id: str, message: str) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.current_task_id = None
        self.error_message.emit(message)
        self.state_changed.emit()
        self.tasks_changed.emit()

    def _merge_batch_results(self) -> None:
        contexts: list[dict] = []
        questions: list[dict] = []
        answer_key: dict[int, str] = {}
        task_ids = self._batch_task_ids or list(self._batch_results)
        for task_id in task_ids:
            result = self._batch_results.get(task_id)
            if not result:
                continue
            contexts.extend(result.get("contexts", []) or [])
            questions.extend(result.get("questions", []) or [])
            raw_answer_key = result.get("answer_key", {}) or {}
            answer_key.update(
                {int(key): str(value) for key, value in raw_answer_key.items()}
            )
        self.result_contexts = contexts
        self.result_questions = questions
        self.result_answer_key = answer_key

    def _start_next_batch_task(self, *, after_task_id: str) -> bool:
        if after_task_id not in self._batch_task_ids:
            return False
        next_index = self._batch_task_ids.index(after_task_id) + 1
        if next_index >= len(self._batch_task_ids):
            return False
        next_task_id = self._batch_task_ids[next_index]
        self.progress_message.emit("Starting next agent request...")
        return self._start_task(next_task_id)

    def run_with_manual_provider(
        self, provider: Callable[[AgentImportPayload], AgentImportResult]
    ) -> None:
        payload = self._build_agent_payload()
        result = provider(payload)
        self.result_contexts = result.contexts
        self.result_questions = result.questions
        self.result_answer_key = result.answer_key
        self.import_ready.emit()

    def list_agent_tasks(self) -> list[ImportAgentTask]:
        return self.task_repo.list_tasks()

    def retry_agent_task(self, task_id: str) -> None:
        task = self.task_repo.queue_for_retry(task_id)
        if task is None:
            self.error_message.emit("Could not retry the selected request.")
            return
        self.tasks_changed.emit()
        if task.id not in self._batch_task_ids:
            self._batch_task_ids = [task.id]
            self._batch_results = {}
        self._start_task(task.id)

    def remove_agent_task(self, task_id: str) -> None:
        if not self.task_repo.delete_task(task_id):
            self.error_message.emit("Could not remove a running or missing request.")
            return
        self.tasks_changed.emit()

    def _parts_with_input(self) -> list[int]:
        return [
            part
            for part, payload in self.part_payloads.items()
            if (payload.part != 2 and payload.question_pages)
            or payload.transcript_pages
        ]

    def _missing_required_answer_sheets(self) -> list[str]:
        parts = self._parts_with_input()
        missing: list[str] = []
        if any(part in (1, 2, 3, 4) for part in parts):
            if not self.answer_sheet.listening_image_path:
                missing.append("Listening")
        if any(part in (5, 6, 7) for part in parts):
            if not self.answer_sheet.reading_image_path:
                missing.append("Reading/Writing")
        return missing

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
