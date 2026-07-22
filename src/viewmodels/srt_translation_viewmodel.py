import json
from typing import Any, Optional

from google.genai import types
from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, QThread, Signal
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.models.exam import ExamSrtChunk


class SrtChunkTranslation(BaseModel):
    index: int
    note: str


class SrtTranslationResponse(BaseModel):
    translations: list[SrtChunkTranslation] = Field(default_factory=list)


class SrtTranslationWorker(QThread):
    progress = Signal(str)
    result_ready = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        chunks: list[ExamSrtChunk],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.chunks = chunks

    def run(self) -> None:
        try:
            result = self._run_agent()
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agent(self) -> dict[int, str]:
        api_key = GEMINI_API_KEY.strip()
        model_name = GEMINI_MODEL.strip() or "gemini-2.5-flash"
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from application config.")

        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("google-genai is not installed.") from exc

        self.progress.emit("Preparing transcript translation request...")
        client = genai.Client(api_key=api_key)
        self.progress.emit("Sending transcript chunks to Gemini...")
        response = client.models.generate_content(
            model=model_name,
            contents=self._build_prompt(),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SrtTranslationResponse,
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = self._response_text(response)
        if not text:
            raise ValueError("Gemini returned an empty transcript translation response.")
        parsed = self._parse_translation_response(response, text)
        requested_indexes = {chunk.index for chunk in self.chunks}
        parsed_translations = [
            translation
            for translation in parsed.translations
            if translation.note.strip()
        ]
        result: dict[int, str] = {}
        for translation in parsed_translations:
            note = translation.note.strip()
            if translation.index in requested_indexes:
                result[translation.index] = note
        if not result and len(parsed_translations) == len(self.chunks):
            return {
                chunk.index: translation.note.strip()
                for chunk, translation in zip(self.chunks, parsed_translations)
            }
        return result

    def _build_prompt(self) -> str:
        rows = [
            {
                "index": chunk.index,
                "text": chunk.text,
            }
            for chunk in self.chunks
        ]
        return f"""
You are a transcript translation assistant for Vietnamese English learners.

Translate each English transcript chunk into natural Vietnamese.
Use the chunk index exactly as provided.

Return ONLY JSON matching this shape:
{{
  "translations": [
    {{"index": 1, "note": "Vietnamese translation"}}
  ]
}}

INPUT:
{json.dumps(rows, ensure_ascii=False, indent=2)}
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

    def _parse_translation_response(
        self, response: Any, text: str
    ) -> SrtTranslationResponse:
        parsed_response = getattr(response, "parsed", None)
        if isinstance(parsed_response, SrtTranslationResponse):
            return parsed_response
        if isinstance(parsed_response, dict):
            return SrtTranslationResponse.model_validate(parsed_response)

        for candidate in self._translation_json_candidates(text):
            try:
                return SrtTranslationResponse.model_validate_json(candidate)
            except ValueError:
                continue

        raise ValueError("Gemini returned transcript translations in an invalid format.")

    def _translation_json_candidates(self, text: str) -> list[str]:
        stripped = text.strip()
        candidates = [stripped]
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                candidates.append("\n".join(lines[1:-1]).strip())
        if (
            len(stripped) >= 2
            and stripped[0] == stripped[-1]
            and stripped[0] in ("'", '"')
        ):
            unwrapped = stripped[1:-1].strip()
            candidates.append(unwrapped)
            candidates.append(unwrapped.replace("\\n", "\n"))
        candidates.append(stripped.replace("\\n", "\n"))
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))


class SrtTranslationViewModel(QObject):
    translation_ready = Signal(object)
    progress_message = Signal(str)
    error_message = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.is_loading = False
        self._worker: Optional[SrtTranslationWorker] = None

    def start_translation(self, chunks: list[ExamSrtChunk]) -> None:
        if self.is_loading:
            return
        targets = [chunk for chunk in chunks if chunk.text.strip()]
        if not targets:
            self.error_message.emit("No transcript text is available.")
            return

        self.is_loading = True
        self._worker = SrtTranslationWorker(targets, self)
        self._worker.progress.connect(self.progress_message.emit)
        self._worker.result_ready.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, translations: dict[int, str]) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.translation_ready.emit(translations)

    def _on_error(self, message: str) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.is_loading = False
        self.error_message.emit(message)
