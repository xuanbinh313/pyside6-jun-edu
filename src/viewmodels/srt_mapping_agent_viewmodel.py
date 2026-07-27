import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal
from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
)
from src.models.exam import (
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    SrtChunkMapping,
    SrtMappingResponseSchema,
)


class SrtMappingAgentWorker(QThread):
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        chunks: list[ExamSrtChunk],
        contexts: list[ExamContext],
        questions_by_context: dict[str, list[ExamQuestion]],
        agent_content_provider: Callable[[dict[str, Any]], dict[str, Any]],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.chunks = chunks
        self.contexts = contexts
        self.questions_by_context = questions_by_context
        self.agent_content_provider = agent_content_provider

    def run(self) -> None:
        try:
            mappings = self._run_agent()
            self.finished.emit(mappings)
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agent(self) -> list[SrtChunkMapping]:
        api_key = GEMINI_API_KEY.strip()
        project = GOOGLE_CLOUD_PROJECT.strip()
        location = GOOGLE_CLOUD_LOCATION.strip()
        model_name = GEMINI_MODEL.strip() or "gemini-2.5-flash"
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from application config.")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is missing from application config.")
        if not location:
            raise ValueError(
                "GOOGLE_CLOUD_LOCATION is missing from application config."
            )

        self.progress.emit("Preparing SRT audio mapping request...")
        prompt = self._build_prompt()
        self.progress.emit("Sending SRT chunks to Gemini...")
        response_payload = self.agent_content_provider(
            {
                "api_key": api_key,
                "model_name": model_name,
                "prompt_text": prompt,
                "file_paths": [],
                "response_schema": SrtMappingResponseSchema,
                "temperature": 0.1,
                "thinking_budget": 0,
            }
        )
        dump_path = self._save_agent_response_file(response_payload)
        self.progress.emit(f"Saved SRT mapping response: {dump_path}")
        text = str(response_payload.get("text") or "").strip()
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
            "context_id | part | questions | type | expected_spoken_title | content_preview",
        ]
        question_rows = [
            "context_id | part | question_number | question_text | A | B | C | D",
        ]
        for context in self.contexts:
            questions = self.questions_by_context.get(context.id, [])
            question_numbers = [
                question.question_number
                for question in questions
            ]
            spoken_title = self._format_part_34_title(context, question_numbers)
            preview = context.content.text.replace("\r", " ").replace("\n", " ")
            preview = " ".join(preview.split())[:500]
            context_rows.append(
                f"{context.id} | {context.part} | {question_numbers} | "
                f"{context.context_type} | {spoken_title} | {preview}"
            )
            for question in questions:
                question_rows.append(self._format_question_row(context, question))

        return f"""
You are a TOEIC audio alignment assistant.

Below is the SRT subtitle table for this exam's audio file.
Each row: index | start_time (s) | end_time (s) | text

[SRT CHUNKS]
{chr(10).join(chunk_rows)}

Below is the context table. Each row is one question-group context.
For TOEIC Part 3 and Part 4, multiple question numbers share one audio block.
The expected_spoken_title column gives the title/preamble line that may be
spoken immediately before the conversation/talk/announcement, for example
"Questions 50-52 refer to the following conversation" or
"Questions 98 through 100 refer to the following announcement".

[CONTEXTS]
{chr(10).join(context_rows)}

Below is the question table. For TOEIC Part 1 and Part 2, the audio segment must
include the complete spoken prompt for the question AND all spoken answer choices
A, B, C, and D for that question. Use the option text to keep the end boundary
after the final spoken choice, not immediately after the question prompt.

[QUESTIONS AND OPTIONS]
{chr(10).join(question_rows)}

TASK:
For each context_id, identify the contiguous range of SRT chunk indexes whose
spoken text corresponds to that context's audio segment.

RULES:
1. Return ONLY contexts where audio is present (listening parts 1-4).
   Omit contexts from reading parts (5, 6, 7) or any context where no matching
   audio is detectable. Do NOT include them in the output at all.
2. For Part 3/4 groups, the context audio segment must include the spoken
   title/preamble chunk when it exists in SRT. Start at the chunk containing
   "Questions X-Y refer to..." or "Question X through Y refer to...", then keep
   the whole conversation/talk/announcement through the last related line.
   Do not start after that title line.
3. The question and option rows are provided so you can match transcript text to
   question numbers and include A-D answer choices in Part 1/2 ranges.
4. Output ONLY the structured JSON. No markdown, no explanation.
""".strip()

    def _format_part_34_title(
        self, context: ExamContext, question_numbers: list[int]
    ) -> str:
        if context.part not in (3, 4) or not question_numbers:
            return ""
        first_question = min(question_numbers)
        last_question = max(question_numbers)
        if context.part == 3:
            target = "conversation"
        else:
            target = "talk/announcement"
        if first_question == last_question:
            return f"Question {first_question} refers to the following {target}."
        return (
            f"Questions {first_question}-{last_question} refer to the following "
            f"{target}; Questions {first_question} through {last_question} "
            f"refer to the following {target}."
        )

    def _format_question_row(
        self, context: ExamContext, question: ExamQuestion
    ) -> str:
        question_text = self._one_line(question.content, 300)
        options = [self._one_line(option, 200) for option in question.options[:4]]
        padded_options = options + [""] * (4 - len(options))
        return (
            f"{context.id} | {context.part} | {question.question_number} | "
            f"{question_text} | {padded_options[0]} | {padded_options[1]} | "
            f"{padded_options[2]} | {padded_options[3]}"
        )

    def _one_line(self, value: str, limit: int) -> str:
        text = value.replace("\r", " ").replace("\n", " ")
        return " ".join(text.split())[:limit]

    def _save_agent_response_file(self, response_payload: dict[str, Any]) -> str:
        response_dir = (
            Path(__file__).resolve().parents[2] / ".codex" / "srt_mapping_responses"
        )
        response_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = response_dir / f"{timestamp}_srt_mapping.json"
        payload = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "response_text": str(response_payload.get("response_text") or ""),
            "candidates": response_payload.get("candidates", []),
            "response": response_payload.get("response", {}),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(path)


class SrtMappingAgentViewModel(QObject):
    mapping_ready = Signal(list)
    progress_message = Signal(str)
    error_message = Signal(str)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        agent_content_provider: Optional[
            Callable[[dict[str, Any]], dict[str, Any]]
        ] = None,
    ) -> None:
        super().__init__(parent)
        self.is_loading = False
        self._worker: Optional[SrtMappingAgentWorker] = None
        self.agent_content_provider = agent_content_provider

    def start_mapping(
        self,
        chunks: list[ExamSrtChunk],
        contexts: list[ExamContext],
        questions_by_context: dict[str, list[ExamQuestion]],
    ) -> None:
        if self.is_loading:
            return
        if not chunks:
            self.error_message.emit("No SRT chunks are available.")
            return
        if not contexts:
            self.error_message.emit("No exam contexts are available.")
            return
        if self.agent_content_provider is None:
            self.error_message.emit("The Agent plugin is missing or disabled.")
            return

        self.is_loading = True
        self._worker = SrtMappingAgentWorker(
            chunks,
            contexts,
            questions_by_context,
            self.agent_content_provider,
            self,
        )
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
