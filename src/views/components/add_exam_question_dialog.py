import json
import tempfile
from pathlib import Path
from typing import Any, Optional

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.models.exam import ExamContext
from src.repositories.sqlite import orm_models as exam_model
from src.repositories.sqlite.database import get_session
from src.utils.helpers import get_local_media_path, optimize_image_to_webp_file
from src.views.components.select_transcript_dialog import SelectTranscriptDialog
from ui_gen.ui_add_exam_question_dialog import Ui_AddExamQuestionDialog


class ImageDropArea(QLabel):
    """Drop/paste target that stores the selected image as a local path."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = ""
        self.image_filename = ""
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setText("Drop image here or press Ctrl+V")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #9aa0a6;
                border-radius: 6px;
                background: #f8f9fa;
                color: #5f6368;
                padding: 16px;
            }
        """)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasImage() or mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self._load_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def paste_from_clipboard(self) -> bool:
        return self._load_from_mime(QApplication.clipboard().mimeData())

    def set_image_path(self, image_path: str, image_filename: str = ""):
        self.image_path = image_path or ""
        self.image_filename = image_filename or Path(self.image_path).name
        if not self.image_path:
            self.setText("Drop image here or press Ctrl+V")
            self.setPixmap(QPixmap())
            self.setToolTip("")
            return

        image = QImage(self.image_path)
        if not image.isNull():
            self._show_preview(image)

    def _load_from_mime(self, mime) -> bool:
        image = QImage()
        source_path = ""
        if mime.hasImage():
            image_data = mime.imageData()
            if isinstance(image_data, QImage):
                image = image_data
            elif isinstance(image_data, QPixmap):
                image = image_data.toImage()
            else:
                image = QImage(image_data)
        elif mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    candidate = QImage(local_path)
                    if not candidate.isNull():
                        image = candidate
                        source_path = local_path
                        break

        if image.isNull():
            return False

        if not source_path:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                source_path = tmp.name
            image.save(source_path)

        self.image_path = source_path
        self.image_filename = Path(source_path).name
        self._show_preview(image)
        return True

    def _show_preview(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(
            pixmap.scaled(
                420,
                180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.setToolTip(self.image_path or "Image loaded")


class AddExamQuestionDialog(QDialog):
    CONTEXT_TYPES = ["READING_PASSAGE", "IMAGE_DIAGRAM", "STANDALONE"]
    QUESTION_TYPES = ["MULTIPLE_CHOICE", "FILL_IN_THE_BLANK", "ESSAY", "RECORDING"]
    LETTERS = ["", "A", "B", "C", "D"]

    def __init__(self, exam_id: Optional[str] = None, context: Optional[ExamContext] = None, parent:Optional[QWidget]=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.context = context
        self.created_question = None
        self.saved_context_id = getattr(context, "id", None)
        self.context_audio_start = 0.0
        self.context_audio_end = 0.0
        self._build_ui()
        self._populate()

    def _build_ui(self):
        self.ui = Ui_AddExamQuestionDialog()
        self.ui.setupUi(self)
        self.setSizeGripEnabled(True)
        self.resize(700, 600)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint)

        self.ui.context_type_combo.addItems(self.CONTEXT_TYPES)
        self.ui.question_type_combo.addItems(self.QUESTION_TYPES)
        self.ui.answer_combo.addItems(self.LETTERS)
        self.ui.paste_image_btn.setIcon(qta.icon("fa5s.paste", color="#1a73e8"))
        self.ui.save_btn.setIcon(qta.icon("fa5s.plus", color="white"))

        self._wrap_content_in_scroll_area()
        self._setup_context_audio_selector()
        self._setup_context_note_editor()

        layout = self.ui.image_page_layout
        idx = layout.indexOf(self.ui.image_drop_placeholder)
        self.ui.image_drop_placeholder.setParent(None)
        self.ui.image_drop_placeholder.deleteLater()
        self.image_drop_area = ImageDropArea(self)
        layout.insertWidget(idx, self.image_drop_area)

        self.question_forms = []
        self.removed_question_ids = set()
        self._setup_question_forms()

        self.ui.context_type_combo.currentIndexChanged.connect(
            self._on_context_type_changed
        )
        self.ui.paste_image_btn.clicked.connect(self._paste_image)
        self.ui.cancel_btn.clicked.connect(self.reject)
        self.ui.save_btn.clicked.connect(self._on_save)
        shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        shortcut.activated.connect(self._paste_image)

    def _icon_button_style(self):
        return """
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                border-radius: 12px;
            }
        """

    def _setup_context_audio_selector(self):
        audio_row = QWidget(self.ui.context_group)
        audio_layout = QHBoxLayout(audio_row)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.setSpacing(8)

        self.context_audio_label = QLabel("No segment selected", audio_row)
        self.context_audio_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        self.context_audio_label.setTextFormat(Qt.TextFormat.PlainText)

        self.context_audio_btn = QPushButton(audio_row)
        self.context_audio_btn.setIcon(qta.icon("fa5s.music", color="#5f6368"))
        self.context_audio_btn.setToolTip("Select audio segment from transcript")
        self.context_audio_btn.setFixedSize(24, 24)
        self.context_audio_btn.setStyleSheet(self._icon_button_style())
        self.context_audio_btn.clicked.connect(self._on_select_context_audio_segment)

        audio_layout.addWidget(self.context_audio_btn)
        audio_layout.addWidget(self.context_audio_label, 1)
        self.ui.context_form.insertRow(3, "Audio Segment:", audio_row)

    def _setup_context_note_editor(self):
        self.context_note_edit = QTextEdit(self.ui.context_group)
        self.context_note_edit.setMinimumHeight(70)
        self.context_note_edit.setPlaceholderText("Context note shown after checking an answer...")
        self.ui.context_form.insertRow(4, "Context Note:", self.context_note_edit)

    def _wrap_content_in_scroll_area(self):
        self.scroll_content = QWidget(self)
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_content_layout.setSpacing(12)

        self.ui.main_layout.removeWidget(self.ui.context_group)
        self.ui.main_layout.removeWidget(self.ui.question_group)
        self.ui.context_group.setParent(self.scroll_content)
        self.ui.question_group.setParent(self.scroll_content)
        self.scroll_content_layout.addWidget(self.ui.context_group)
        self.scroll_content_layout.addWidget(self.ui.question_group)
        self.scroll_content_layout.addStretch()

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setWidget(self.scroll_content)
        self.ui.main_layout.insertWidget(1, self.scroll_area, 1)

    def _setup_question_forms(self):
        self.note_edit = QTextEdit(self.ui.question_group)
        self.note_edit.setMinimumHeight(70)
        self.note_edit.setPlaceholderText("Explain why the answer is correct...")
        self.ui.question_form.addRow("Note:", self.note_edit)

        self.add_question_btn = QPushButton("Add Question")
        self.add_question_btn.setIcon(qta.icon("fa5s.plus", color="#1a73e8"))
        self.add_question_btn.clicked.connect(lambda: self._add_question_form())
        self.ui.question_form.addRow(self.add_question_btn)

        first_form = {
            "id": None,
            "container": self.ui.question_group,
            "number": self.ui.question_number_spin,
            "type": self.ui.question_type_combo,
            "answer": self.ui.answer_combo,
            "content": self.ui.content_edit,
            "note": self.note_edit,
            "options": [
                self.ui.option_a_edit,
                self.ui.option_b_edit,
                self.ui.option_c_edit,
                self.ui.option_d_edit,
            ],
            "delete_btn": None,
        }
        self.question_forms.append(first_form)

    def _add_question_form(self, question=None):
        group = QGroupBox()
        group.setTitle("Question")
        form = QFormLayout(group)
        form.setSpacing(8)

        header = QWidget(group)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()
        delete_btn = QPushButton()
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color="#ea4335"))
        delete_btn.setToolTip("Delete question")
        delete_btn.setFixedSize(28, 28)
        header_layout.addWidget(delete_btn)
        form.addRow(header)

        number_spin = QSpinBox(group)
        number_spin.setRange(1, 9999)
        type_combo = QComboBox(group)
        type_combo.addItems(self.QUESTION_TYPES)
        answer_combo = QComboBox(group)
        answer_combo.addItems(self.LETTERS)
        content_edit = QTextEdit(group)
        content_edit.setMinimumHeight(80)
        content_edit.setPlaceholderText("Question stem...")
        note_edit = QTextEdit(group)
        note_edit.setMinimumHeight(70)
        note_edit.setPlaceholderText("Explain why the answer is correct...")
        option_edits = [QLineEdit(group) for _ in range(4)]

        form.addRow("Question No.:", number_spin)
        form.addRow("Type:", type_combo)
        form.addRow("Correct Answer:", answer_combo)
        form.addRow(content_edit)
        form.addRow("Note:", note_edit)
        for letter, edit in zip(["A:", "B:", "C:", "D:"], option_edits):
            form.addRow(letter, edit)

        question_form = {
            "id": None,
            "container": group,
            "number": number_spin,
            "type": type_combo,
            "answer": answer_combo,
            "content": content_edit,
            "note": note_edit,
            "options": option_edits,
            "delete_btn": delete_btn,
        }
        self.question_forms.append(question_form)
        delete_btn.clicked.connect(lambda: self._remove_question_form(question_form))
        self.scroll_content_layout.insertWidget(
            self.scroll_content_layout.count() - 1, group
        )
        if question:
            self._populate_question_form(question_form, question)
        else:
            self._renumber_new_question_form(question_form)
        return question_form

    def _remove_question_form(self, question_form):
        if len(self.question_forms) <= 1:
            self._clear_question_form(question_form)
            return
        if question_form["id"]:
            self.removed_question_ids.add(question_form["id"])
        self.question_forms.remove(question_form)
        question_form["container"].deleteLater()

    def _clear_question_form(self, question_form):
        question_form["id"] = None
        question_form["content"].clear()
        question_form["note"].clear()
        for edit in question_form["options"]:
            edit.clear()
        question_form["answer"].setCurrentIndex(0)

    def _renumber_new_question_form(self, question_form):
        max_number = max(
            (form["number"].value() for form in self.question_forms), default=0
        )
        question_form["number"].setValue(max_number + 1)

    def _populate(self):
        if self.context:
            self.setWindowTitle("Edit Exam Context")
            self.ui.header_label.setText("Edit Context and Questions")
            self.ui.save_btn.setText("Save")
            self._populate_from_context()
        else:
            self.setWindowTitle("Add Exam Question")
            self._populate_defaults()
        self._on_context_type_changed(self.ui.context_type_combo.currentIndex())

    def _populate_defaults(self):
        session = get_session()
        try:
            max_q = (
                session.query(exam_model.ExamQuestion.question_number)
                .join(
                    exam_model.ExamContext,
                    exam_model.ExamQuestion.context_id == exam_model.ExamContext.id,
                )
                .filter(exam_model.ExamContext.exam_id == self.exam_id)
                .order_by(exam_model.ExamQuestion.question_number.desc())
                .first()
            )
            max_ctx = (
                session.query(exam_model.ExamContext.index)
                .filter(exam_model.ExamContext.exam_id == self.exam_id)
                .order_by(exam_model.ExamContext.index.desc())
                .first()
            )
            self.ui.question_number_spin.setValue((max_q[0] if max_q else 0) + 1)
            self.ui.context_index_spin.setValue((max_ctx[0] if max_ctx else -1) + 1)
            self.ui.part_spin.setValue(1)
        finally:
            session.close()

    def _as_plain_dict(self, value: object) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped

        model_dict = getattr(value, "dict", None)
        if callable(model_dict):
            dumped = model_dict()
            if isinstance(dumped, dict):
                return dumped

        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(decoded, dict):
                return decoded

        return {}

    def _populate_from_context(self):
        ctx = self.context
        if not ctx:
            return
        type_idx = self.ui.context_type_combo.findText(str(ctx.context_type))
        self.ui.context_type_combo.setCurrentIndex(type_idx if type_idx >= 0 else 0)
        self.ui.part_spin.setValue(ctx.part or 1)
        self.ui.context_index_spin.setValue(ctx.index or 0)
        content = self._as_plain_dict(ctx.content)
        meta = self._as_plain_dict(ctx.additional_meta)
        self.context_audio_start = float(meta.get("audio_start", 0.0) or 0.0)
        self.context_audio_end = float(meta.get("audio_end", 0.0) or 0.0)
        self.context_note_edit.setPlainText(str(meta.get("note", "") or ""))
        self._refresh_context_audio_ui()
        context_text = str(content.get("text", "") or "")
        self.ui.context_text_edit.setPlainText(context_text)
        self.ui.image_description_edit.setPlainText(context_text)
        image_filename = str(content.get("image_filename", "") or "")
        image_path = ""
        if image_filename:
            local_image_path = get_local_media_path(image_filename)
            if local_image_path.is_file():
                image_path = str(local_image_path)
        if not image_path:
            image_path = str(content.get("image_path", "") or "")
        self.image_drop_area.set_image_path(image_path, image_filename)

        session = get_session()
        try:
            questions = (
                session.query(exam_model.ExamQuestion)
                .filter(exam_model.ExamQuestion.context_id == ctx.id)
                .order_by(exam_model.ExamQuestion.question_number.asc())
                .all()
            )
            if not questions:
                self._populate_defaults()
                return
            self._populate_question_form(self.question_forms[0], questions[0])
            for question in questions[1:]:
                self._add_question_form(question)
            self.created_question = questions[0]
            for question in questions:
                session.expunge(question)
        finally:
            session.close()

    def _populate_question_form(self, question_form, question):
        question_form["id"] = question.id
        question_form["number"].setValue(question.question_number)
        q_type_idx = question_form["type"].findText(question.question_type)
        question_form["type"].setCurrentIndex(q_type_idx if q_type_idx >= 0 else 0)
        ans_idx = question_form["answer"].findText(question.correct_answer or "")
        question_form["answer"].setCurrentIndex(ans_idx if ans_idx >= 0 else 0)
        question_form["content"].setPlainText(question.content or "")
        meta = (
            question.additional_meta
            if isinstance(question.additional_meta, dict)
            else {}
        )
        question_form["note"].setPlainText(str(meta.get("note", "")))
        options = question.options or []
        if isinstance(options, str):
            options = json.loads(options)
        for i, edit in enumerate(question_form["options"]):
            edit.setText(options[i] if i < len(options) else "")

    def _on_context_type_changed(self, index):
        ctx_type = self.ui.context_type_combo.currentText()
        if ctx_type == "IMAGE_DIAGRAM":
            self.ui.context_stack.setCurrentWidget(self.ui.image_page)
        else:
            self.ui.context_stack.setCurrentWidget(self.ui.text_page)

    def _paste_image(self):
        if self.ui.context_type_combo.currentText() != "IMAGE_DIAGRAM":
            return
        if not self.image_drop_area.paste_from_clipboard():
            QMessageBox.warning(
                self, "No Image", "Clipboard does not contain an image."
            )

    def _context_content(self):
        ctx_type = self.ui.context_type_combo.currentText()
        if ctx_type == "IMAGE_DIAGRAM":
            if not self.image_drop_area.image_path:
                raise ValueError("Please drop or paste an image.")
            filename = self._save_diagram_image_file()
            return {
                "text": self.ui.image_description_edit.toPlainText().strip(),
                "image_filename": filename,
            }
        text = self.ui.context_text_edit.toPlainText().strip()
        if ctx_type != "STANDALONE" and not text:
            raise ValueError("Context text cannot be empty.")
        return {"text": text}

    def _save_diagram_image_file(self) -> str:
        current_filename = self.image_drop_area.image_filename
        current_path = Path(self.image_drop_area.image_path)
        if current_filename and current_path == get_local_media_path(current_filename):
            return current_filename

        filename = optimize_image_to_webp_file(
            self.image_drop_area.image_path, current_filename
        )
        self.image_drop_area.set_image_path(
            str(get_local_media_path(filename)), filename
        )
        return filename

    def _select_audio_segment(self):
        dialog = SelectTranscriptDialog(self.exam_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_chunks:
            first = dialog.selected_chunks[0]
            last = dialog.selected_chunks[-1]
            return float(first.start_time), float(last.end_time)
        return None

    def _format_audio_segment_text(self, start: float, end: float) -> str:
        if end > 0.0:
            return f"{start:.2f}s - {end:.2f}s"
        return "No segment selected"

    def _refresh_context_audio_ui(self):
        self.context_audio_label.setText(
            self._format_audio_segment_text(
                self.context_audio_start, self.context_audio_end
            )
        )
        color = "#1a73e8" if self.context_audio_end > 0.0 else "#5f6368"
        self.context_audio_btn.setIcon(qta.icon("fa5s.music", color=color))

    def _on_select_context_audio_segment(self):
        segment = self._select_audio_segment()
        if not segment:
            return
        self.context_audio_start, self.context_audio_end = segment
        self._refresh_context_audio_ui()

    def _on_save(self):
        question_values = []
        for form in self.question_forms:
            content = form["content"].toPlainText().strip()
            if not content:
                QMessageBox.warning(
                    self, "Validation", "Question content cannot be empty."
                )
                return
            q_type = form["type"].currentText()
            options = [edit.text().strip() for edit in form["options"]]
            if q_type == "MULTIPLE_CHOICE" and any(not opt for opt in options):
                QMessageBox.warning(
                    self,
                    "Validation",
                    "All four options are required for multiple choice.",
                )
                return
            question_values.append(
                {
                    "id": form["id"],
                    "question_number": form["number"].value(),
                    "question_type": q_type,
                    "content": content,
                    "note": form["note"].toPlainText().strip(),
                    "options": options,
                    "correct_answer": form["answer"].currentText(),
                }
            )

        question_numbers = [item["question_number"] for item in question_values]
        if len(question_numbers) != len(set(question_numbers)):
            QMessageBox.warning(
                self, "Validation", "Question numbers must be unique in this context."
            )
            return

        try:
            ctx_content = self._context_content()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation", str(exc))
            return

        session = get_session()
        try:
            if self.saved_context_id:
                db_ctx = (
                    session.query(exam_model.ExamContext)
                    .filter(exam_model.ExamContext.id == self.saved_context_id)
                    .first()
                )
                if not db_ctx:
                    QMessageBox.critical(
                        self, "Error", "Context not found in database."
                    )
                    return
            else:
                db_ctx = exam_model.ExamContext(exam_id=self.exam_id)
            db_ctx.part = self.ui.part_spin.value()
            db_ctx.context_type = self.ui.context_type_combo.currentText()
            db_ctx.content = ctx_content
            db_ctx.index = self.ui.context_index_spin.value()
            db_ctx.additional_meta = exam_model.AdditionalMeta(
                audio_start=self.context_audio_start,
                audio_end=self.context_audio_end,
                note=self.context_note_edit.toPlainText().strip(),
            )
            session.add(db_ctx)
            if db_ctx.context_type == "IMAGE_DIAGRAM":
                image_filename = str(ctx_content.get("image_filename", "") or "")
                if image_filename:
                    existing_media = (
                        session.query(exam_model.MediaFile)
                        .filter(exam_model.MediaFile.filename == image_filename)
                        .first()
                    )
                    if not existing_media:
                        session.add(
                            exam_model.MediaFile(
                                filename=image_filename,
                                user_id=db_ctx.user_id,
                                dirty=True,
                            )
                        )
            session.flush()

            if self.removed_question_ids:
                session.query(exam_model.ExamQuestion).filter(
                    exam_model.ExamQuestion.id.in_(self.removed_question_ids)
                ).delete(synchronize_session="fetch")

            saved_questions = []
            for value in question_values:
                db_q = None
                if value["id"]:
                    db_q = (
                        session.query(exam_model.ExamQuestion)
                        .filter(exam_model.ExamQuestion.id == value["id"])
                        .first()
                    )
                if not db_q:
                    db_q = exam_model.ExamQuestion(context_id=db_ctx.id)
                    session.add(db_q)

                db_q.context_id = db_ctx.id
                db_q.question_number = value["question_number"]
                db_q.question_type = value["question_type"]
                db_q.content = value["content"]
                db_q.options = value["options"]
                db_q.correct_answer = value["correct_answer"]
                db_q.additional_meta = {"note": str(value["note"])}
                saved_questions.append(db_q)

            session.commit()
            session.refresh(db_ctx)
            for db_q in saved_questions:
                session.refresh(db_q)
            session.expunge(db_ctx)
            for db_q in saved_questions:
                session.expunge(db_q)
            self.context = db_ctx
            self.saved_context_id = db_ctx.id
            self.created_question = saved_questions[0] if saved_questions else None
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self, "Error Saving", f"Could not save question:\n{exc}"
            )
            return
        finally:
            session.close()

        self.accept()
