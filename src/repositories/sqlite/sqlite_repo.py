import datetime
from typing import Any, Optional, cast

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models.exam import (
    ContextSchema,
    Exam,
    ExamAttempt,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    MediaFile,
    QuestionSchema,
    UserAnswer,
    Vocabulary,
)
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


def _mediafile_from_orm(db_mediafile: orm.MediaFile) -> MediaFile:
    return MediaFile.model_validate(db_mediafile)


def _exam_from_orm(db_exam: orm.Exam) -> Exam:
    return Exam.model_validate(db_exam)


def _chunk_from_orm(db_chunk: orm.ExamSrtChunk) -> ExamSrtChunk:
    return ExamSrtChunk.model_validate(db_chunk)


def _context_from_orm(db_context: orm.ExamContext) -> ExamContext:
    return ExamContext.model_validate(db_context)


def _question_from_orm(db_question: orm.ExamQuestion) -> ExamQuestion:
    return ExamQuestion.model_validate(db_question)


def _attempt_from_orm(db_attempt: orm.ExamAttempt) -> ExamAttempt:
    return ExamAttempt.model_validate(db_attempt)


def _answer_from_orm(db_answer: orm.UserAnswer) -> UserAnswer:
    return UserAnswer.model_validate(db_answer)


def _vocabulary_from_orm(db_vocabulary: orm.Vocabulary) -> Vocabulary:
    source_text: Optional[str] = None
    if db_vocabulary.context is not None:
        content = db_vocabulary.context.content
        text_value = content.get("text")
        if isinstance(text_value, str):
            source_text = text_value
    return Vocabulary.model_validate(
        {
            "id": db_vocabulary.id,
            "word": db_vocabulary.word,
            "meaning": db_vocabulary.meaning,
            "status": db_vocabulary.status,
            "context_id": db_vocabulary.context_id,
            "created_at": db_vocabulary.created_at,
            "user_id": db_vocabulary.user_id,
            "source_text": source_text,
        }
    )


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


def _normalize_segment_words(segment: dict[str, Any]) -> list[dict[str, object]]:
    raw_words = segment.get("words", [])
    words: list[dict[str, object]] = []
    if not isinstance(raw_words, list):
        return words

    for raw_word in raw_words:
        if not isinstance(raw_word, dict):
            continue
        words.append(
            {
                "word": str(raw_word.get("word", "")),
                "start": float(raw_word.get("start", 0.0)),
                "end": float(raw_word.get("end", 0.0)),
            }
        )
    return words


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

    def add_vocabulary(
        self, word: str, context_id: Optional[str] = None
    ) -> Vocabulary:
        normalized_word = word.strip()
        if not normalized_word:
            raise ValueError("Vocabulary word cannot be empty.")

        session = get_session()
        try:
            db_vocabulary = orm.Vocabulary(
                word=normalized_word,
                context_id=context_id,
            )
            session.add(db_vocabulary)
            session.commit()
            session.refresh(db_vocabulary)
            return _vocabulary_from_orm(db_vocabulary)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_vocabulary(self) -> list[Vocabulary]:
        session = get_session()
        try:
            rows = (
                session.query(orm.Vocabulary)
                .options(joinedload(orm.Vocabulary.context))
                .order_by(orm.Vocabulary.created_at.desc())
                .all()
            )
            return [_vocabulary_from_orm(row) for row in rows]
        finally:
            session.close()

    def update_vocabulary_status(self, vocab_id: str, status: int) -> None:
        if status not in range(1, 6):
            raise ValueError("Vocabulary status must be between 1 and 5.")
        self._update_vocabulary(vocab_id, status=status)

    def update_vocabulary_meaning(self, vocab_id: str, meaning: str) -> None:
        self._update_vocabulary(vocab_id, meaning=meaning.strip() or None)

    def _update_vocabulary(self, vocab_id: str, **values: Any) -> None:
        session = get_session()
        try:
            updated = (
                session.query(orm.Vocabulary)
                .filter(orm.Vocabulary.id == vocab_id)
                .update(values)
            )
            if not updated:
                raise ValueError("Vocabulary item was not found.")
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_vocabulary(self, vocab_id: str) -> None:
        session = get_session()
        try:
            row = session.get(orm.Vocabulary, vocab_id)
            if row is not None:
                session.delete(row)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_exam_details(
        self, exam_id: str
    ) -> tuple[Optional[Exam], list[ExamSrtChunk], list[ExamContext], list[ExamQuestion]]:
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
        exam_id: Optional[str],
        title: str,
        description: Optional[str],
        duration_minutes: int,
        is_published: bool,
        audio_name: Optional[str] = None,
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
                        user_id=chunk.user_id,
                        additional_meta=cast(
                            orm.AdditionalSrtChunkMeta,
                            chunk.additional_meta.model_dump(),
                        ),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_srt_chunks(self, exam_id: str) -> list[ExamSrtChunk]:
        session = get_session()
        try:
            rows = (
                session.query(orm.ExamSrtChunk)
                .filter(orm.ExamSrtChunk.exam_id == exam_id)
                .order_by(orm.ExamSrtChunk.index.asc())
                .all()
            )
            return [_chunk_from_orm(chunk) for chunk in rows]
        finally:
            session.close()

    def get_exam_take_data(
        self, exam_id: str, user_id: Optional[str] = None
    ) -> tuple[
        Optional[Exam],
        list[ExamContext],
        list[ExamQuestion],
        list[ExamSrtChunk],
        list[str],
        list[ExamAttempt],
    ]:
        session = get_session()
        try:
            db_exam = session.query(orm.Exam).filter(orm.Exam.id == exam_id).first()
            if not db_exam:
                return None, [], [], [], [], []

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
                .join(
                    orm.ExamContext, orm.ExamQuestion.context_id == orm.ExamContext.id
                )
                .filter(orm.ExamContext.exam_id == exam_id)
                .order_by(orm.ExamQuestion.question_number.asc())
                .all()
            ]
            chunks = [
                _chunk_from_orm(chunk)
                for chunk in session.query(orm.ExamSrtChunk)
                .filter(orm.ExamSrtChunk.exam_id == exam_id)
                .order_by(orm.ExamSrtChunk.index.asc(), orm.ExamSrtChunk.start_time.asc())
                .all()
            ]
            tag_rows = (
                session.query(orm.UserQuestionTag.tag_name)
                .join(
                    orm.ExamContext,
                    orm.UserQuestionTag.context_id == orm.ExamContext.id,
                )
                .filter(
                    orm.UserQuestionTag.user_id == user_id,
                    orm.ExamContext.exam_id == exam_id,
                )
                .distinct()
                .order_by(orm.UserQuestionTag.tag_name.asc())
                .all()
            )
            attempts = self._list_attempts(session, exam_id, user_id)
            exam = _exam_from_orm(db_exam)
            exam.contexts = contexts
            exam.srt_chunks = chunks
            return (
                exam,
                contexts,
                questions,
                chunks,
                [row[0] for row in tag_rows],
                attempts,
            )
        finally:
            session.close()

    def list_question_tags_by_question(
        self, exam_id: str, user_id: Optional[str] = None
    ) -> dict[str, set[str]]:
        session = get_session()
        try:
            rows = (
                session.query(orm.ExamQuestion.id, orm.UserQuestionTag.tag_name)
                .join(orm.ExamContext, orm.ExamQuestion.context_id == orm.ExamContext.id)
                .join(
                    orm.UserQuestionTag,
                    orm.UserQuestionTag.context_id == orm.ExamContext.id,
                )
                .filter(
                    orm.UserQuestionTag.user_id == user_id,
                    orm.ExamContext.exam_id == exam_id,
                )
                .all()
            )
            result: dict[str, set[str]] = {}
            for question_id, tag_name in rows:
                result.setdefault(str(question_id), set()).add(str(tag_name))
            return result
        finally:
            session.close()

    def save_exam_attempt(
        self,
        *,
        exam_id: str,
        user_id: Optional[str],
        total_correct: int,
        total_questions: int,
        final_score: Optional[float],
        duration_seconds: int,
        answers: list[dict[str, Any]],
    ) -> tuple[str, list[ExamAttempt]]:
        session = get_session()
        try:
            attempt = orm.ExamAttempt(
                user_id=user_id,
                exam_id=exam_id,
                total_correct=total_correct,
                total_questions=total_questions,
                final_score=final_score,
                duration_seconds=duration_seconds,
                created_at=str(datetime.datetime.now(datetime.timezone.utc)),
                dirty=False,
            )
            session.add(attempt)
            session.flush()

            for answer in answers:
                session.add(
                    orm.UserAnswer(
                        attempt_id=attempt.id,
                        question_id=str(answer["question_id"]),
                        user_choice=answer.get("user_choice"),
                        is_correct=bool(answer.get("is_correct", False)),
                        dirty=False,
                    )
                )

            session.commit()
            attempt_id = str(attempt.id)
            return attempt_id, self._list_attempts(session, exam_id, user_id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_attempt_with_answers(
        self, exam_id: str, user_id: Optional[str], attempt_id: str
    ) -> tuple[Optional[ExamAttempt], list[tuple[UserAnswer, ExamQuestion, ExamContext]]]:
        session = get_session()
        try:
            attempt = (
                session.query(orm.ExamAttempt)
                .filter(
                    orm.ExamAttempt.id == attempt_id,
                    orm.ExamAttempt.exam_id == exam_id,
                    orm.ExamAttempt.user_id == user_id,
                )
                .first()
            )
            if not attempt:
                return None, []

            rows = (
                session.query(orm.UserAnswer, orm.ExamQuestion, orm.ExamContext)
                .join(orm.ExamQuestion, orm.UserAnswer.question_id == orm.ExamQuestion.id)
                .join(orm.ExamContext, orm.ExamQuestion.context_id == orm.ExamContext.id)
                .filter(orm.UserAnswer.attempt_id == attempt_id)
                .order_by(orm.ExamContext.part.asc(), orm.ExamQuestion.question_number.asc())
                .all()
            )
            return (
                _attempt_from_orm(attempt),
                [
                    (
                        _answer_from_orm(user_answer),
                        _question_from_orm(question),
                        _context_from_orm(context),
                    )
                    for user_answer, question, context in rows
                ],
            )
        finally:
            session.close()

    def save_external_aligned_exam(
        self,
        *,
        target_exam_id: Optional[str],
        title: str,
        description: str,
        duration_minutes: int,
        audio_name: str,
        segments: list[dict[str, Any]],
    ) -> str:
        session = get_session()
        try:
            if target_exam_id:
                exam = (
                    session.query(orm.Exam)
                    .filter(orm.Exam.id == target_exam_id)
                    .first()
                )
                if not exam:
                    raise ValueError("Target exam not found.")
                exam.audio_name = audio_name
                session.query(orm.ExamSrtChunk).filter(
                    orm.ExamSrtChunk.exam_id == exam.id
                ).delete(synchronize_session="fetch")
            else:
                exam = orm.Exam(
                    title=title,
                    description=description,
                    duration_minutes=duration_minutes,
                    audio_name=audio_name,
                    is_published=False,
                )
                session.add(exam)
                session.flush()

            session.add(
                orm.MediaFile(
                    filename=audio_name,
                    user_id=exam.user_id,
                    dirty=True,
                )
            )

            for index, segment in enumerate(segments):
                session.add(
                    orm.ExamSrtChunk(
                        exam_id=exam.id,
                        index=index,
                        start_time=float(segment.get("start", 0.0)),
                        end_time=float(segment.get("end", 0.0)),
                        text=str(segment.get("text", "")),
                        additional_meta=cast(
                            orm.AdditionalSrtChunkMeta,
                            {"words": _normalize_segment_words(segment)},
                        ),
                    )
                )

            session.commit()
            return str(exam.id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _list_attempts(
        self, session: Any, exam_id: str, user_id: Optional[str]
    ) -> list[ExamAttempt]:
        rows = (
            session.query(orm.ExamAttempt)
            .filter(
                orm.ExamAttempt.user_id == user_id,
                orm.ExamAttempt.exam_id == exam_id,
            )
            .order_by(orm.ExamAttempt.created_at.desc())
            .all()
        )
        return [_attempt_from_orm(row) for row in rows]

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
        self, exam_id: str, selected_tags: Optional[list[str]] = None
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

    def get_add_question_defaults(self, exam_id: Optional[str]) -> tuple[int, int]:
        if not exam_id:
            return 1, 0

        session = get_session()
        try:
            max_q = (
                session.query(orm.ExamQuestion.question_number)
                .join(
                    orm.ExamContext,
                    orm.ExamQuestion.context_id == orm.ExamContext.id,
                )
                .filter(orm.ExamContext.exam_id == exam_id)
                .order_by(orm.ExamQuestion.question_number.desc())
                .first()
            )
            max_ctx = (
                session.query(orm.ExamContext.index)
                .filter(orm.ExamContext.exam_id == exam_id)
                .order_by(orm.ExamContext.index.desc())
                .first()
            )
            next_question_number = (int(max_q[0]) if max_q else 0) + 1
            next_context_index = (int(max_ctx[0]) if max_ctx else -1) + 1
            return next_question_number, next_context_index
        finally:
            session.close()

    def save_context_questions(
        self,
        *,
        exam_id: Optional[str],
        context_id: Optional[str],
        part: int,
        context_type: str,
        content: dict[str, Any],
        index: int,
        additional_meta: dict[str, Any],
        questions: list[dict[str, Any]],
        removed_question_ids: set[str],
    ) -> tuple[ExamContext, list[ExamQuestion]]:
        session = get_session()
        try:
            db_ctx: Optional[orm.ExamContext] = None
            if context_id:
                db_ctx = (
                    session.query(orm.ExamContext)
                    .filter(orm.ExamContext.id == context_id)
                    .first()
                )
                if not db_ctx:
                    raise ValueError("Context not found in database.")
            else:
                if not exam_id:
                    raise ValueError("Cannot add questions before the exam is saved.")
                db_ctx = orm.ExamContext(exam_id=exam_id)

            db_ctx.part = part
            db_ctx.context_type = context_type
            db_ctx.content = cast(orm.ExamContent, content)
            db_ctx.index = index
            db_ctx.additional_meta = cast(orm.AdditionalMeta, additional_meta)
            session.add(db_ctx)
            if db_ctx.context_type == "IMAGE_DIAGRAM":
                image_filename = str(content.get("image_filename", "") or "")
                if image_filename:
                    existing_media = (
                        session.query(orm.MediaFile)
                        .filter(orm.MediaFile.filename == image_filename)
                        .first()
                    )
                    if not existing_media:
                        session.add(
                            orm.MediaFile(
                                filename=image_filename,
                                user_id=db_ctx.user_id,
                                dirty=True,
                            )
                        )
            session.flush()

            if removed_question_ids:
                session.query(orm.ExamQuestion).filter(
                    orm.ExamQuestion.id.in_(removed_question_ids)
                ).delete(synchronize_session="fetch")

            saved_questions: list[orm.ExamQuestion] = []
            for value in questions:
                db_q: Optional[orm.ExamQuestion] = None
                question_id = str(value.get("id", "") or "")
                if question_id:
                    db_q = (
                        session.query(orm.ExamQuestion)
                        .filter(orm.ExamQuestion.id == question_id)
                        .first()
                    )
                if not db_q:
                    db_q = orm.ExamQuestion(context_id=db_ctx.id)
                    session.add(db_q)

                db_q.context_id = db_ctx.id
                db_q.question_number = int(value["question_number"])
                db_q.question_type = str(value["question_type"])
                db_q.content = str(value["content"])
                db_q.options = [str(option) for option in value["options"]]
                db_q.correct_answer = str(value["correct_answer"])
                db_q.additional_meta = orm.QuestionAdditionalMeta(
                    note=str(value.get("note", ""))
                )
                saved_questions.append(db_q)

            session.commit()
            session.refresh(db_ctx)
            for db_q in saved_questions:
                session.refresh(db_q)
            return (
                _context_from_orm(db_ctx),
                [_question_from_orm(question) for question in saved_questions],
            )
        except Exception:
            session.rollback()
            raise
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
    ) -> Optional[ExamContext]:
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
        self, exam_id: str, contexts_data: list[ContextSchema], questions_data: list[QuestionSchema]
    ) -> dict[str, list[int]]:
        session = get_session()
        try:
            question_numbers = [
                (q_data.get("question_number") or idx + 1)
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
                new_ctx: Optional[orm.ExamContext] = None
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
