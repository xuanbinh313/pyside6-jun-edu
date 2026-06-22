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
