from __future__ import annotations

from src.repositories.base_repo import IExamRepository


class SupabaseExamRepository(IExamRepository):
    """Placeholder for the stateless Supabase-backed repository implementation."""

    def __init__(self, client):
        self.client = client

    def list_exams(self, search_query: str = ""):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def delete_exam(self, exam_id: str) -> None:
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def get_exam_details(self, exam_id: str):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def save_exam(self, **kwargs) -> str:
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def replace_srt_chunks(self, exam_id: str, chunks) -> None:
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def list_question_tags(self):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def list_contexts(self, exam_id: str, selected_tags=None):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def list_questions_for_context(self, context_id: str):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def get_context_question_numbers(self, context_id: str):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def delete_contexts_and_questions(self, context_ids, question_ids) -> None:
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def update_correct_answers(self, exam_id: str, answer_key: dict[int, str]):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")

    def import_contexts_and_questions(
        self, exam_id: str, contexts_data: list[dict], questions_data: list[dict]
    ):
        raise NotImplementedError("Supabase exam repository is not implemented yet.")
