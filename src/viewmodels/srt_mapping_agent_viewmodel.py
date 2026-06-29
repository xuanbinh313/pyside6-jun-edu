import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google.genai import types
from pydantic import BaseModel
from PySide6.QtCore import QObject, QThread, Signal
from src.models.exam import (
    ExamContext,
    ExamSrtChunk,
    SrtChunkMapping,
    SrtMappingResponseSchema,
)

load_dotenv()


class SrtMappingAgentWorker(QThread):
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        chunks: list[ExamSrtChunk],
        contexts: list[ExamContext],
        questions_by_context: dict[str, list[int]],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.chunks = chunks
        self.contexts = contexts
        self.questions_by_context = questions_by_context

    def run(self) -> None:
        try:
            mappings = self._run_agent()
            self.finished.emit(mappings)
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agent(self) -> list[SrtChunkMapping]:
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

        self.progress.emit("Preparing SRT audio mapping request...")
        client = genai.Client(api_key=api_key)
        prompt = self._build_prompt()
        self.progress.emit("Sending SRT chunks to Gemini...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SrtMappingResponseSchema,
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        dump_path = self._save_agent_response_file(response)
        self.progress.emit(f"Saved SRT mapping response: {dump_path}")
        text = self._response_text(response)
        if not text:
            raise ValueError("Gemini returned an empty SRT mapping response.")
        parsed = SrtMappingResponseSchema.model_validate_json(text)
        return parsed.mappings

    def _build_prompt(self) -> str:
        chunk_rows = [
            f"{chunk.index} | {chunk.start_time:.3f} | {chunk.end_time:.3f} | {chunk.text}"
            for chunk in self.chunks
        ]
        context_rows = [
            "context_id | part | questions | type | content_preview",
        ]
        for context in self.contexts:
            questions = self.questions_by_context.get(context.id, [])
            preview = context.content.text.replace("\r", " ").replace("\n", " ")
            preview = " ".join(preview.split())[:500]
            context_rows.append(
                f"{context.id} | {context.part} | {questions} | "
                f"{context.context_type} | {preview}"
            )

        return f"""
You are a TOEIC audio alignment assistant.

Below is the SRT subtitle table for this exam's audio file.
Each row: index | start_time (s) | end_time (s) | text

[SRT CHUNKS]
{chr(10).join(chunk_rows)}

Below is the context table. Each row is one question-group context.
For TOEIC Part 3 and Part 4, multiple question numbers share one audio block.

[CONTEXTS]
{chr(10).join(context_rows)}

TASK:
For each context_id, identify the contiguous range of SRT chunk indexes whose
spoken text corresponds to that context's audio segment.

RULES:
1. Return ONLY contexts where audio is present (listening parts 1-4).
   Omit contexts from reading parts (5, 6, 7) or any context where no matching
   audio is detectable. Do NOT include them in the output at all.
2. For Part 3/4 groups sharing one audio block, the same start_chunk_index and
   end_chunk_index may appear for multiple context_ids.
3. The questions list is provided so you can match transcript text to question numbers.
4. Output ONLY the structured JSON. No markdown, no explanation.
""".strip()

    def _response_text(self, response: Any) -> str:
        text = self._response_text_from_parts(response)
        if text:
            return text
        response_text = getattr(response, "text", "")
        if response_text:
            return str(response_text).strip()
        return ""

    def _response_text_from_parts(self, response: Any) -> str:
        candidates = getattr(response, "candidates", None) or []
        chunks: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    chunks.append(str(part_text))
        return "\n".join(chunks).strip()

    def _save_agent_response_file(self, response: Any) -> str:
        response_dir = (
            Path(__file__).resolve().parents[2] / ".codex" / "srt_mapping_responses"
        )
        response_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = response_dir / f"{timestamp}_srt_mapping.json"
        payload = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "response_text": self._response_text_from_parts(response),
            "candidates": self._dump_response_candidates(response),
            "response": self._json_safe(response),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(path)

    def _dump_response_candidates(self, response: Any) -> list[Any]:
        candidates = getattr(response, "candidates", None) or []
        return [self._json_safe(candidate) for candidate in candidates]

    def _json_safe(self, value: Any) -> Any:
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


class SrtMappingAgentViewModel(QObject):
    mapping_ready = Signal(list)
    progress_message = Signal(str)
    error_message = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.is_loading = False
        self._worker: Optional[SrtMappingAgentWorker] = None

    def start_mapping(
        self,
        chunks: list[ExamSrtChunk],
        contexts: list[ExamContext],
        questions_by_context: dict[str, list[int]],
    ) -> None:
        if self.is_loading:
            return
        if not chunks:
            self.error_message.emit("No SRT chunks are available.")
            return
        if not contexts:
            self.error_message.emit("No exam contexts are available.")
            return

        self.is_loading = True
        self._worker = SrtMappingAgentWorker(chunks, contexts, questions_by_context, self)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def resolve_times(
        self,
        mappings: list[SrtChunkMapping],
        chunks: list[ExamSrtChunk],
    ) -> list[tuple[str, float, float]]:
        chunk_by_index = {chunk.index: chunk for chunk in chunks}
        result: list[tuple[str, float, float]] = []
        for mapping in mappings:
            start_chunk = chunk_by_index.get(mapping.start_chunk_index)
            end_chunk = chunk_by_index.get(mapping.end_chunk_index)
            if (
                start_chunk is not None
                and end_chunk is not None
                and end_chunk.end_time > 0.0
            ):
                result.append(
                    (mapping.context_id, start_chunk.start_time, end_chunk.end_time)
                )
        return result

    def _on_finished(self, mappings: list[SrtChunkMapping]) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.mapping_ready.emit(mappings)

    def _on_error(self, message: str) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.error_message.emit(message)
