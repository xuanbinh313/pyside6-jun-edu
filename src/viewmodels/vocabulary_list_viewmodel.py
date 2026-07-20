from __future__ import annotations

import json
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, QThread, Signal
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.models.exam import Vocabulary
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class VocabularyTranslation(BaseModel):
    id: str
    meaning: str


class VocabularyTranslationResponse(BaseModel):
    translations: list[VocabularyTranslation] = Field(default_factory=list)


class VocabularyTranslateWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, vocabulary: list[Vocabulary], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.vocabulary = vocabulary

    def run(self) -> None:
        try:
            translations = self._run_agent()
            self.finished.emit(translations)
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agent(self) -> dict[str, str]:
        api_key = GEMINI_API_KEY.strip()
        model_name = GEMINI_MODEL.strip() or "gemini-2.5-flash"
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from application config.")

        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("google-genai is not installed.") from exc

        self.progress.emit("Preparing vocabulary translation request...")
        client = genai.Client(api_key=api_key)
        self.progress.emit("Sending vocabulary to Gemini...")
        response = client.models.generate_content(
            model=model_name,
            contents=self._build_prompt(),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VocabularyTranslationResponse,
                temperature=0.1,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = self._response_text(response)
        if not text:
            raise ValueError("Gemini returned an empty vocabulary translation response.")
        parsed = VocabularyTranslationResponse.model_validate_json(text)
        result: dict[str, str] = {}
        requested_ids = {item.id for item in self.vocabulary}
        for translation in parsed.translations:
            meaning = translation.meaning.strip()
            if translation.id in requested_ids and meaning:
                result[translation.id] = meaning
        return result

    def _build_prompt(self) -> str:
        rows = [
            {
                "id": item.id,
                "word": item.word,
                "source_context": item.source_text or "",
            }
            for item in self.vocabulary
        ]
        return f"""
You are a vocabulary translation assistant for English learners.

Translate each English vocabulary word or phrase into natural Vietnamese.
Use source_context only to choose the correct meaning when a word is ambiguous.

Return ONLY JSON matching this shape:
{{
  "translations": [
    {{"id": "same id from input", "meaning": "Vietnamese meaning"}}
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


class VocabularyListViewModel(QObject):
    data_changed = Signal()
    error_occurred = Signal(str)
    translation_started = Signal(int)
    translation_progress = Signal(str)
    translation_finished = Signal(int)

    def __init__(self, repo: IExamRepository | None = None) -> None:
        super().__init__()
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.vocabulary: list[Vocabulary] = []
        self._all_vocabulary: list[Vocabulary] = []
        self._search_query = ""
        self.is_translating = False
        self._translate_worker: VocabularyTranslateWorker | None = None

    def load_vocabulary(self) -> None:
        try:
            self._all_vocabulary = self.repo.list_vocabulary()
            self._apply_filter()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def set_search_query(self, query: str) -> None:
        self._search_query = query.strip().casefold()
        self._apply_filter()

    def update_status(self, vocab_id: str, status: int) -> None:
        try:
            self.repo.update_vocabulary_status(vocab_id, status)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def update_meaning(self, vocab_id: str, meaning: str) -> None:
        try:
            self.repo.update_vocabulary_meaning(vocab_id, meaning)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def delete_vocabulary(self, vocab_id: str) -> None:
        try:
            self.repo.delete_vocabulary(vocab_id)
            self.load_vocabulary()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def translate_empty_meanings(self) -> None:
        if self.is_translating:
            return
        targets = [
            item
            for item in self._all_vocabulary
            if not (item.meaning or "").strip()
        ]
        if not targets:
            self.translation_finished.emit(0)
            return

        self.is_translating = True
        self.translation_started.emit(len(targets))
        self._translate_worker = VocabularyTranslateWorker(targets, self)
        self._translate_worker.progress.connect(self.translation_progress.emit)
        self._translate_worker.finished.connect(self._on_translation_finished)
        self._translate_worker.error.connect(self._on_translation_error)
        self._translate_worker.start()

    def _apply_filter(self) -> None:
        query = self._search_query
        self.vocabulary = [
            item
            for item in self._all_vocabulary
            if not query
            or query in item.word.casefold()
            or query in (item.meaning or "").casefold()
            or query in (item.source_text or "").casefold()
        ]
        self.data_changed.emit()

    def _on_translation_finished(self, translations: dict[str, str]) -> None:
        updated_count = 0
        try:
            for vocab_id, meaning in translations.items():
                self.repo.update_vocabulary_meaning(vocab_id, meaning)
                updated_count += 1
            self.load_vocabulary()
            self.translation_finished.emit(updated_count)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self._clear_translate_worker()

    def _on_translation_error(self, message: str) -> None:
        self.error_occurred.emit(message)
        self._clear_translate_worker()

    def _clear_translate_worker(self) -> None:
        worker = self._translate_worker
        self._translate_worker = None
        self.is_translating = False
        if worker is not None:
            worker.deleteLater()
