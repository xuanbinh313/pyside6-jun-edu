import re
from typing import Optional

from src.models.exam import Exam, ExamContext, ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class ExamTranscriptViewModel:
    def __init__(self, exam: Optional[Exam] = None, repo: Optional[IExamRepository] = None):
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.exam: Optional[Exam] = exam
        self.srt_chunks: list[ExamSrtChunk] = []

    def load_chunks(self, chunks: list[ExamSrtChunk]):
        self.srt_chunks = chunks

    def duplicate_chunk(self, chunk: ExamSrtChunk):
        list_idx = self.srt_chunks.index(chunk)

        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=chunk.index + 1,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text,
            hint=getattr(chunk, "hint", None),
            user_id=chunk.user_id,
            additional_meta=chunk.additional_meta.model_copy(deep=True),
        )
        self.srt_chunks.insert(list_idx + 1, new_chunk)
        self._renumber_chunks()
        return list_idx + 1, new_chunk

    def delete_chunk(self, chunk: ExamSrtChunk):
        list_idx = self.srt_chunks.index(chunk)
        removed_chunk = self.srt_chunks.pop(list_idx)
        self._renumber_chunks()
        return list_idx, removed_chunk

    def split_chunk(self, chunk: ExamSrtChunk, cursor_position: int):
        list_idx = self.srt_chunks.index(chunk)
        split_position = max(0, min(cursor_position, len(chunk.text)))
        left_text = chunk.text[:split_position].rstrip()
        right_text = chunk.text[split_position:].lstrip()
        if not left_text or not right_text:
            return None, None

        words = chunk.additional_meta.words
        left_word_count = self._word_count(left_text)
        left_words = [word.model_copy(deep=True) for word in words[:left_word_count]]
        right_words = [word.model_copy(deep=True) for word in words[left_word_count:]]

        original_end = chunk.end_time
        if right_words:
            split_time = right_words[0].start
        elif left_words:
            split_time = left_words[-1].end
        else:
            ratio = split_position / max(len(chunk.text), 1)
            split_time = chunk.start_time + ((chunk.end_time - chunk.start_time) * ratio)

        chunk.text = left_text
        chunk.end_time = max(chunk.start_time, float(split_time))
        chunk.additional_meta.words = left_words

        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=chunk.index + 1,
            start_time=chunk.end_time,
            end_time=original_end,
            text=right_text,
            hint=getattr(chunk, "hint", None),
            user_id=chunk.user_id,
            additional_meta={"words": right_words},
        )
        self.srt_chunks.insert(list_idx + 1, new_chunk)
        self._renumber_chunks()
        return list_idx + 1, new_chunk

    def merge_chunk(self, chunk: ExamSrtChunk):
        list_idx = self.srt_chunks.index(chunk)
        if list_idx >= len(self.srt_chunks) - 1:
            return None, None

        next_chunk = self.srt_chunks[list_idx + 1]
        chunk.text = f"{chunk.text} {next_chunk.text}"
        chunk.end_time = next_chunk.end_time
        chunk.additional_meta.words.extend(
            word.model_copy(deep=True) for word in next_chunk.additional_meta.words
        )

        self.srt_chunks.pop(list_idx + 1)
        self._renumber_chunks()
        return list_idx, next_chunk

    def _renumber_chunks(self) -> None:
        for index, chunk in enumerate(self.srt_chunks, start=1):
            chunk.index = index

    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r"\S+", text))

    def save_chunks(self):
        if not self.exam or not self.exam.id:
            return

        self.repo.replace_srt_chunks(self.exam.id, self.srt_chunks)

    @property
    def exam_id(self) -> Optional[str]:
        return self.exam.id if self.exam else None

    def list_contexts(self, selected_tags: Optional[list[str]] = None) -> list[ExamContext]:
        exam_id = self.exam_id
        if not exam_id:
            return []
        return self.repo.list_contexts(exam_id, selected_tags or [])

    def context_question_numbers(self, context_id: str) -> list[int]:
        return self.repo.get_context_question_numbers(context_id)

    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ):
        return self.repo.update_context_audio_segment(
            context_id, audio_start, audio_end
        )
