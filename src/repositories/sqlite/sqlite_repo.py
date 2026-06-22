from __future__ import annotations

from sqlalchemy.orm import joinedload

from src.models.exam import Exam, ExamContext, ExamQuestion, ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite.database import get_session
from src.repositories.sqlite import orm_models as orm


def _exam_from_orm(db_exam: orm.Exam) -> Exam:
    return Exam(
        id=db_exam.id,  # type: ignore
        title=db_exam.title,  # type: ignore
        description=db_exam.description,  # type: ignore
        full_audio_url=db_exam.full_audio_url,  # type: ignore
        duration_minutes=db_exam.duration_minutes,  # type: ignore
        is_published=db_exam.is_published,  # type: ignore
        user_id=db_exam.user_id,  # type: ignore
        created_at=db_exam.created_at,  # type: ignore
        updated_at=db_exam.updated_at,  # type: ignore
    )


def _chunk_from_orm(db_chunk: orm.ExamSrtChunk) -> ExamSrtChunk:
    return ExamSrtChunk(
        id=db_chunk.id,  # type: ignore
        exam_id=db_chunk.exam_id,  # type: ignore
        index=db_chunk.index,  # type: ignore
        start_time=db_chunk.start_time,  # type: ignore
        end_time=db_chunk.end_time,  # type: ignore
        text=db_chunk.text,  # type: ignore
        hint=db_chunk.hint,  # type: ignore
        user_id=db_chunk.user_id,  # type: ignore
    )


def _context_from_orm(db_context: orm.ExamContext) -> ExamContext:
    return ExamContext(
        id=db_context.id,  # type: ignore
        exam_id=db_context.exam_id,  # type: ignore
        part=db_context.part,  # type: ignore
        context_type=db_context.context_type,  # type: ignore
        content=db_context.content,  # type: ignore
        index=db_context.index,  # type: ignore
        additional_meta=db_context.additional_meta  # type: ignore
        or {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
        user_id=db_context.user_id,  # type: ignore
    )


def _question_from_orm(db_question: orm.ExamQuestion) -> ExamQuestion:
    question = ExamQuestion(
        id=db_question.id,  # type: ignore
        context_id=db_question.context_id,  # type: ignore
        question_number=db_question.question_number,  # type: ignore
        question_type=db_question.question_type,  # type: ignore
        content=db_question.content,  # type: ignore
        options=db_question.options or [],  # type: ignore
        correct_answer=db_question.correct_answer,  # type: ignore
        additional_meta=db_question.additional_meta or {"note": ""},  # type: ignore
        user_id=db_question.user_id,  # type: ignore
    )
    if db_question.context:
        question.context = _context_from_orm(db_question.context)
    return question


class SQLiteExamRepository(IExamRepository):
    def list_exams(self, search_query: str = "") -> list[Exam]:
        session = get_session()
        try:
            query = session.query(orm.Exam)
            if search_query:
                query = query.filter(orm.Exam.title.ilike(f"%{search_query}%"))
            return [_exam_from_orm(exam) for exam in query.all()]
        finally:
            session.close()

    def delete_exam(self, exam_id: str) -> None:
        session = get_session()
        try:
            exam = session.query(orm.Exam).filter(orm.Exam.id == exam_id).first()
            if exam:
                session.delete(exam)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_exam_details(
        self, exam_id: str
    ) -> tuple[Exam | None, list[ExamSrtChunk], list[ExamContext], list[ExamQuestion]]:
        session = get_session()
        try:
            db_exam = (
                session.query(orm.Exam)
                .options(joinedload(orm.Exam.srt_chunks))
                .filter(orm.Exam.id == exam_id)
                .first()
            )
            if not db_exam:
                return None, [], [], []

            exam = _exam_from_orm(db_exam)
            chunks = sorted(
                (_chunk_from_orm(chunk) for chunk in db_exam.srt_chunks),
                key=lambda chunk: chunk.index,
            )
            contexts = [
                _context_from_orm(context)
                for context in session.query(orm.ExamContext)
                .filter(orm.ExamContext.exam_id == exam_id)
                .order_by(orm.ExamContext.part.asc(), orm.ExamContext.index.asc())
                .all()
            ]
            questions = [
                _question_from_orm(question)
                for question in session.query(orm.ExamQuestion)
                .options(joinedload(orm.ExamQuestion.context))
                .join(
                    orm.ExamContext, orm.ExamQuestion.context_id == orm.ExamContext.id
                )
                .filter(orm.ExamContext.exam_id == exam_id)
                .order_by(orm.ExamQuestion.question_number.asc())
                .all()
            ]
            exam.srt_chunks = chunks
            exam.contexts = contexts
            return exam, chunks, contexts, questions
        finally:
            session.close()

    def save_exam(
        self,
        *,
        exam_id: str | None,
        title: str,
        description: str | None,
        duration_minutes: int,
        is_published: bool,
        full_audio_url: str | None = None,
    ) -> str:
        session = get_session()
        try:
            db_exam = None
            if exam_id:
                db_exam = session.query(orm.Exam).filter(orm.Exam.id == exam_id).first()
            if not db_exam:
                db_exam = orm.Exam(title=title)
                session.add(db_exam)

            db_exam.title = title
            db_exam.description = description
            db_exam.duration_minutes = duration_minutes
            db_exam.is_published = is_published
            db_exam.full_audio_url = full_audio_url
            session.commit()
            return db_exam.id  # type: ignore
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def replace_srt_chunks(self, exam_id: str, chunks: list[ExamSrtChunk]) -> None:
        session = get_session()
        try:
            session.query(orm.ExamSrtChunk).filter(
                orm.ExamSrtChunk.exam_id == exam_id
            ).delete()
            for chunk in chunks:
                session.add(
                    orm.ExamSrtChunk(
                        exam_id=exam_id,
                        index=chunk.index,
                        start_time=chunk.start_time,
                        end_time=chunk.end_time,
                        text=chunk.text,
                        hint=chunk.hint,
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
