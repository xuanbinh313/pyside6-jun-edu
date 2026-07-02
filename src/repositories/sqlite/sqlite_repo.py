from __future__ import annotations

import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models.exam import Exam, ExamContext, ExamQuestion, ExamSrtChunk
from src.repositories.base_repo import IExamRepository
from src.repositories.sqlite import orm_models as orm
from src.repositories.sqlite.database import get_session
from src.utils.helpers import (
    decode_data_url,
    extension_from_data_url,
    get_local_media_path,
    optimize_image_to_webp_file,
    unique_media_filename,
)


def _exam_from_orm(db_exam: orm.Exam) -> Exam:
    return Exam.model_validate(db_exam)


def _chunk_from_orm(db_chunk: orm.ExamSrtChunk) -> ExamSrtChunk:
    return ExamSrtChunk.model_validate(db_chunk)


def _context_from_orm(db_context: orm.ExamContext) -> ExamContext:
    return ExamContext.model_validate(db_context)


def _question_from_orm(db_question: orm.ExamQuestion) -> ExamQuestion:
    return ExamQuestion.model_validate(db_question)


def _save_imported_diagram_media(ctx_data: dict) -> str:
    content = ctx_data.get("content")
    if not isinstance(content, dict):
        return ""

    image_path = str(
        content.get("_source_image_path", "") or content.get("image_path", "") or ""
    )
    if image_path:
        filename = content.get("filename") or content.get("image_filename")
        media_filename = optimize_image_to_webp_file(image_path, str(filename or ""))
        content["image_filename"] = media_filename
        content["image_path"] = str(get_local_media_path(media_filename))
        content.pop("_source_image_path", None)
        content.pop("image_data_url", None)
        return media_filename

    image_data_url = str(content.get("image_data_url", "") or "")
    if not image_data_url.startswith("data:"):
        return ""

    filename = content.get("filename") or content.get("image_filename")
    if not filename:
        filename = f"diagram{extension_from_data_url(image_data_url)}"
    unique_filename = unique_media_filename(str(filename))
    get_local_media_path(unique_filename).write_bytes(decode_data_url(image_data_url))
    content["image_filename"] = unique_filename
    content["image_path"] = str(get_local_media_path(unique_filename))
    content.pop("image_data_url", None)
    content.pop("_source_image_path", None)
    return unique_filename


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
        audio_name: str | None = None,
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
            db_exam.audio_name = audio_name
            db_exam.updated_at = str(datetime.datetime.now(datetime.timezone.utc))
            if not db_exam.created_at:
                db_exam.created_at = str(datetime.datetime.now(datetime.timezone.utc))
            if audio_name:
                existing_media = (
                    session.query(orm.MediaFile)
                    .filter(orm.MediaFile.filename == audio_name)
                    .first()
                )
                if not existing_media:
                    session.add(
                        orm.MediaFile(
                            filename=audio_name,
                            user_id=db_exam.user_id,
                            dirty=True,
                        )
                    )
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

    def list_question_tags(self) -> list[str]:
        session = get_session()
        try:
            rows = session.query(orm.UserQuestionTag.tag_name).distinct().all()
            return sorted(row[0] for row in rows)
        finally:
            session.close()

    def list_question_tags_for_context(self, context_id: str) -> list[str]:
        session = get_session()
        try:
            rows = (
                session.query(orm.UserQuestionTag.tag_name)
                .filter(orm.UserQuestionTag.context_id == context_id)
                .order_by(orm.UserQuestionTag.tag_name.asc())
                .all()
            )
            return [row[0] for row in rows]
        finally:
            session.close()

    def set_context_tag(self, context_id: str, tag_name: str, enabled: bool) -> None:
        session = get_session()
        try:
            existing = (
                session.query(orm.UserQuestionTag)
                .filter(
                    orm.UserQuestionTag.context_id == context_id,
                    orm.UserQuestionTag.tag_name == tag_name,
                )
                .first()
            )
            if enabled and not existing:
                session.add(
                    orm.UserQuestionTag(
                        context_id=context_id,
                        tag_name=tag_name,
                        dirty=1,
                    )
                )
            elif not enabled and existing:
                session.delete(existing)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_contexts(
        self, exam_id: str, selected_tags: list[str] | None = None
    ) -> list[ExamContext]:
        session = get_session()
        try:
            if not selected_tags:
                query = session.query(orm.ExamContext).filter(
                    orm.ExamContext.exam_id == exam_id
                )
            else:
                query = (
                    session.query(orm.ExamContext)
                    .join(
                        orm.UserQuestionTag,
                        orm.ExamContext.id == orm.UserQuestionTag.context_id,
                    )
                    .filter(
                        orm.ExamContext.exam_id == exam_id,
                        orm.UserQuestionTag.tag_name.in_(selected_tags),
                    )
                    .distinct()
                )
            rows = query.order_by(
                orm.ExamContext.part.asc(), orm.ExamContext.index.asc()
            ).all()
            return [_context_from_orm(context) for context in rows]
        finally:
            session.close()

    def list_questions_for_context(self, context_id: str) -> list[ExamQuestion]:
        session = get_session()
        try:
            rows = (
                session.query(orm.ExamQuestion)
                .options(joinedload(orm.ExamQuestion.context))
                .filter(orm.ExamQuestion.context_id == context_id)
                .order_by(orm.ExamQuestion.question_number.asc())
                .all()
            )
            return [_question_from_orm(question) for question in rows]
        finally:
            session.close()

    def get_context_question_numbers(self, context_id: str) -> list[int]:
        session = get_session()
        try:
            rows = (
                session.query(orm.ExamQuestion.question_number)
                .filter(orm.ExamQuestion.context_id == context_id)
                .order_by(orm.ExamQuestion.question_number.asc())
                .all()
            )
            return [row[0] for row in rows]
        finally:
            session.close()

    def delete_contexts_and_questions(
        self, context_ids: list[str], question_ids: list[str]
    ) -> None:
        session = get_session()
        try:
            for context_id in context_ids:
                session.query(orm.UserQuestionTag).filter(
                    orm.UserQuestionTag.context_id == context_id
                ).delete(synchronize_session="fetch")
                session.query(orm.ExamQuestion).filter(
                    orm.ExamQuestion.context_id == context_id
                ).delete(synchronize_session="fetch")
                session.query(orm.ExamContext).filter(
                    orm.ExamContext.id == context_id
                ).delete(synchronize_session="fetch")
            if question_ids:
                session.query(orm.ExamQuestion).filter(
                    orm.ExamQuestion.id.in_(question_ids)
                ).delete(synchronize_session="fetch")
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_context_audio_segment(
        self, context_id: str, audio_start: float, audio_end: float
    ) -> ExamContext | None:
        session = get_session()
        try:
            db_ctx = (
                session.query(orm.ExamContext)
                .filter(orm.ExamContext.id == context_id)
                .first()
            )
            if not db_ctx:
                return None

            existing_meta = (
                db_ctx.additional_meta
                if isinstance(db_ctx.additional_meta, dict)
                else {}
            )
            db_ctx.additional_meta = {
                "audio_start": audio_start,
                "audio_end": audio_end,
                "note": str(existing_meta.get("note", "")),
            }
            session.commit()
            return _context_from_orm(db_ctx)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_correct_answers(
        self, exam_id: str, answer_key: dict[int, str]
    ) -> list[int]:
        if not answer_key:
            return []

        session = get_session()
        try:
            stmt = (
                select(orm.ExamQuestion)
                .join(
                    orm.ExamContext,
                    orm.ExamQuestion.context_id == orm.ExamContext.id,
                )
                .filter(orm.ExamContext.exam_id == exam_id)
            )
            updated_numbers: list[int] = []
            for question in session.scalars(stmt).all():
                question_number = int(question.question_number or 0)
                answer = answer_key.get(question_number)
                if not answer:
                    continue
                question.correct_answer = answer
                updated_numbers.append(question_number)
            session.commit()
            return sorted(updated_numbers)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def import_contexts_and_questions(
        self, exam_id: str, contexts_data: list[dict], questions_data: list[dict]
    ) -> dict:
        session = get_session()
        try:
            question_numbers = [
                int(q_data.get("question_number", idx + 1))
                for idx, q_data in enumerate(questions_data)
            ]
            import_duplicates = sorted(
                {
                    number
                    for number in question_numbers
                    if number and question_numbers.count(number) > 1
                }
            )
            if import_duplicates:
                return {"duplicate_numbers": import_duplicates}
            stmt = (
                select(orm.ExamQuestion)
                .join(
                    orm.ExamContext,
                    orm.ExamQuestion.context_id == orm.ExamContext.id,
                )
                .filter(orm.ExamContext.exam_id == exam_id)
            )
            existing_questions = session.scalars(stmt).all()
            existing_by_number: dict[int, orm.ExamQuestion] = {
                cast(int, question.question_number): question
                for question in existing_questions
            }

            llm_to_real_id: dict[str, str] = {}
            for q_data in questions_data:
                llm_ctx_id = q_data.get("llm_context_id")
                question_number = int(q_data.get("question_number", 0) or 0)
                existing_q = existing_by_number.get(question_number)
                if llm_ctx_id and existing_q:
                    llm_to_real_id[str(llm_ctx_id)] = str(existing_q.context_id)

            for ctx_data in contexts_data:
                llm_id = ctx_data.get("llm_id", "")
                new_ctx: orm.ExamContext | None = None
                real_ctx_id = llm_to_real_id.get(str(llm_id)) if llm_id else None
                if real_ctx_id:
                    new_ctx = (
                        session.query(orm.ExamContext)
                        .filter(orm.ExamContext.id == real_ctx_id)
                        .first()
                    )
                    if not new_ctx:
                        real_ctx_id = None

                if not real_ctx_id:
                    new_ctx = orm.ExamContext(exam_id=exam_id)
                    session.add(new_ctx)
                if new_ctx:
                    new_ctx.part = int(ctx_data.get("part", 1))
                    new_ctx.context_type = ctx_data.get(
                        "context_type", "READING_PASSAGE"
                    )
                    new_ctx.content = ctx_data.get("content", {})
                    new_ctx.index = ctx_data.get("index", 0)
                    new_ctx.additional_meta = ctx_data.get(
                        "additional_meta",
                        {"audio_start": 0.0, "audio_end": 0.0, "note": ""},
                    )
                    new_ctx.user_id = ctx_data.get("user_id")
                    if new_ctx.context_type == "IMAGE_DIAGRAM":
                        media_filename = _save_imported_diagram_media(ctx_data)
                        if media_filename:
                            new_ctx.content = ctx_data.get("content", {})
                            session.add(
                                orm.MediaFile(
                                    filename=media_filename,
                                    user_id=new_ctx.user_id,
                                    dirty=True,
                                )
                            )
                    session.flush()
                    if llm_id:
                        llm_to_real_id[str(llm_id)] = str(new_ctx.id)

            updated_numbers: list[int] = []
            created_count = 0
            for idx, q_data in enumerate(questions_data):
                llm_ctx_id = q_data.get("llm_context_id")
                real_ctx_id = (
                    llm_to_real_id.get(str(llm_ctx_id)) if llm_ctx_id else None
                )
                if not real_ctx_id:
                    new_ctx = orm.ExamContext(
                        exam_id=exam_id,
                        part=1,
                        context_type="STANDALONE",
                        content={"text": ""},
                        index=idx,
                        additional_meta={
                            "audio_start": 0.0,
                            "audio_end": 0.0,
                            "note": "",
                        },
                        user_id=q_data.get("user_id"),
                    )
                    session.add(new_ctx)
                    session.flush()
                    real_ctx_id = new_ctx.id

                additional_meta = q_data.get("additional_meta") or {"note": ""}
                additional_meta = orm.QuestionAdditionalMeta(
                    note=str(additional_meta.get("note", ""))
                )
                question_number = int(q_data.get("question_number", idx + 1))

                db_q = existing_by_number.get(question_number)
                if db_q:
                    updated_numbers.append(question_number)
                else:
                    db_q = orm.ExamQuestion()
                    session.add(db_q)
                    created_count += 1

                db_q.context_id = real_ctx_id
                db_q.question_number = question_number
                db_q.question_type = q_data.get("question_type", "MULTIPLE_CHOICE")
                db_q.content = q_data["content"]
                db_q.options = q_data["options"]
                db_q.correct_answer = q_data.get("correct_answer", "")
                db_q.additional_meta = additional_meta
                db_q.user_id = q_data.get("user_id")

            session.commit()
            return {
                "context_count": len(contexts_data),
                "created_count": created_count,
                "updated_numbers": updated_numbers,
                "duplicate_numbers": [],
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
