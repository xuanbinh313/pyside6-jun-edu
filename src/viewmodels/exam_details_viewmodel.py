import re
from typing import Optional

from PySide6.QtCore import QObject, Signal
from src.models.exam import (
    ContextSchema,
    Exam,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    QuestionSchema,
    Vocabulary,
)
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.sqlite_repo import SQLiteExamRepository


class ExamDetailsViewModel(QObject):
    data_loaded = Signal()
    data_saved = Signal()

    def __init__(self, exam_id: Optional[str] = None, repo: Optional[IExamRepository] = None):
        super().__init__()
        self.repo: IExamRepository = repo or SQLiteExamRepository()
        self.exam_id = exam_id
        self.exam = None
        self.srt_chunks: list[ExamSrtChunk] = []
        self.contexts: list[ExamContext] = []
        self.questions: list[ExamQuestion] = []

    def load_exam(self):
        if self.exam_id:
            self.exam, self.srt_chunks, self.contexts, self.questions = (
                self.repo.get_exam_details(self.exam_id)
            )
        else:
            self.exam = Exam(title="")
            self.srt_chunks = []
            self.contexts = []
            self.questions = []
        self.data_loaded.emit()

    def save_exam(
        self, title: str, description: str, duration_minutes: int, is_published: bool, audio_name: Optional[str] = None
    ):
        self.exam_id = self.repo.save_exam(
            exam_id=self.exam_id,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            is_published=is_published,
            audio_name=audio_name,
        )
        self.data_saved.emit()

    def save_chunks(self):
        if not self.exam_id:
            return

        self.repo.replace_srt_chunks(self.exam_id, self.srt_chunks)

    def list_question_tags(self) -> list[str]:
        return self.repo.list_question_tags()

    def list_question_tags_for_context(self, context_id: str) -> list[str]:
        return self.repo.list_question_tags_for_context(context_id)

    def set_context_tag(self, context_id: str, tag_name: str, enabled: bool) -> None:
        self.repo.set_context_tag(context_id, tag_name, enabled)

    def add_vocabulary(
        self, word: str, context_id: Optional[str] = None
    ) -> Vocabulary:
        return self.repo.add_vocabulary(word, context_id)

    def list_contexts(self, selected_tags: Optional[list[str]] = None) -> list[ExamContext]:
        if not self.exam_id:
            return []
        return self.repo.list_contexts(self.exam_id, selected_tags)

    def list_questions_for_context(self, context_id: str) -> list[ExamQuestion]:
        return self.repo.list_questions_for_context(context_id)

    def context_question_numbers(self, context_id: str) -> list[int]:
        return self.repo.get_context_question_numbers(context_id)

    def delete_contexts_and_questions(
        self, context_ids: list[str], question_ids: list[str]
    ) -> None:
        self.repo.delete_contexts_and_questions(context_ids, question_ids)

    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ):
        return self.repo.update_context_audio_segment(
            context_id, audio_start, audio_end
        )

    def update_correct_answers(self, answer_key: dict[int, str]) -> list[int]:
        if not self.exam_id or not answer_key:
            return []
        return self.repo.update_correct_answers(self.exam_id, answer_key)

    def import_contexts_and_questions(
        self, contexts_data: list[ContextSchema], questions_data: list[QuestionSchema]
    ) -> dict:
        if not self.exam_id:
            raise ValueError("Cannot import questions before the exam is saved.")
        return self.repo.import_contexts_and_questions(
            self.exam_id, contexts_data, questions_data
        )

    def duplicate_chunk(self, chunk: ExamSrtChunk):
        list_idx = self.srt_chunks.index(chunk)

        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=chunk.index + 1,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text,
            note=chunk.note,
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
        chunk.note = ""
        chunk.end_time = max(chunk.start_time, float(split_time))
        chunk.additional_meta.words = left_words

        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=chunk.index + 1,
            start_time=chunk.end_time,
            end_time=original_end,
            text=right_text,
            note="",
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
        chunk.note = "\n".join(
            note for note in (chunk.note.strip(), next_chunk.note.strip()) if note
        )
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
