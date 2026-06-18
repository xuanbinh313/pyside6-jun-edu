import json
import os
import re
import random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTextBrowser, QScrollArea,
    QMessageBox, QDialog, QFrame, QButtonGroup, QRadioButton,
    QSizePolicy, QMenu, QCheckBox, QLineEdit, QAbstractItemView,
    QComboBox, QFormLayout, QDialogButtonBox, QTextEdit, QSplitter,
    QGroupBox
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Qt, QTimer, QPoint, QFile
from PySide6.QtGui import QColor, QPalette, QCursor
import qtawesome as qta
from .ui_exam_groups_widget import Ui_ExamGroupsWidget
from src.models.database import get_session
from src.views.components.import_questions_dialog import ImportQuestionsDialog
import src.models.exam as exam_model


# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract audio timestamps from additional_meta JSON
# ─────────────────────────────────────────────────────────────────────────────
def _get_audio_meta(question):
    """Return (audio_start_seconds, audio_end_seconds) from additional_meta."""
    meta = question.additional_meta or {}
    return float(meta.get("audio_start", 0.0)), float(meta.get("audio_end", 0.0))


# ─────────────────────────────────────────────────────────────────────────────
# OptionWidget — shuffled ABCD radio buttons for a single question
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# TagMenuPopup — floating menu to manage question tags
# ─────────────────────────────────────────────────────────────────────────────
class TagMenuPopup(QDialog):
    def __init__(self, question, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.question = question
        self.user_id = "local_user"
        self.setStyleSheet("""
            QDialog {
                border: 1px solid #dadce0;
                background-color: white;
                border-radius: 6px;
            }
        """)
        self.setFixedWidth(200)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Manage Tags")
        title.setStyleSheet("font-weight: bold; color: #1a73e8; font-size: 12px;")
        layout.addWidget(title)

        # List of tags checkable
        self.tags_layout = QVBoxLayout()
        self.tags_layout.setSpacing(4)
        layout.addLayout(self.tags_layout)

        # Add input field
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Add new tag...")
        self.new_tag_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
        """)
        self.new_tag_input.returnPressed.connect(self._on_add_tag)
        layout.addWidget(self.new_tag_input)

        # Load existing tags and question's tags
        self._load_tags()

    def _load_tags(self):
        # Clear tags layout
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                del item

        session = get_session()
        try:
            # All unique tags for this user
            all_tags_rows = session.query(exam_model.UserQuestionTag.tag_name).filter(
                exam_model.UserQuestionTag.user_id == self.user_id
            ).distinct().all()
            all_tags = [r[0] for r in all_tags_rows]

            # Tags currently applied to this question
            current_tags_rows = session.query(exam_model.UserQuestionTag.tag_name).filter(
                exam_model.UserQuestionTag.user_id == self.user_id,
                exam_model.UserQuestionTag.question_id == self.question.id
            ).all()
            current_tags = set(r[0] for r in current_tags_rows)

            for tag_name in all_tags:
                cb = QCheckBox(tag_name)
                cb.setChecked(tag_name in current_tags)
                cb.setStyleSheet("font-size: 11px; color: #3c4043;")
                cb.stateChanged.connect(lambda state, t=tag_name: self._on_tag_state_changed(t, state))
                self.tags_layout.addWidget(cb)
        finally:
            session.close()

    def _on_tag_state_changed(self, tag_name, state):
        session = get_session()
        try:
            if state == Qt.CheckState.Checked.value:
                # Add tag
                exists = session.query(exam_model.UserQuestionTag).filter(
                    exam_model.UserQuestionTag.user_id == self.user_id,
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name
                ).first()
                if not exists:
                    new_tag = exam_model.UserQuestionTag(
                        user_id=self.user_id,
                        question_id=self.question.id,
                        tag_name=tag_name,
                        dirty=1
                    )
                    session.add(new_tag)
                    session.commit()
            else:
                # Delete tag
                session.query(exam_model.UserQuestionTag).filter(
                    exam_model.UserQuestionTag.user_id == self.user_id,
                    exam_model.UserQuestionTag.question_id == self.question.id,
                    exam_model.UserQuestionTag.tag_name == tag_name
                ).delete()
                session.commit()
        finally:
            session.close()

        # Notify parent widget to refresh filter if necessary
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_tag_changed"):
                parent_widget.on_question_tag_changed()
                break
            parent_widget = parent_widget.parent()

    def _on_add_tag(self):
        tag_name = self.new_tag_input.text().strip()
        if not tag_name:
            return
        
        session = get_session()
        try:
            exists = session.query(exam_model.UserQuestionTag).filter(
                exam_model.UserQuestionTag.user_id == self.user_id,
                exam_model.UserQuestionTag.question_id == self.question.id,
                exam_model.UserQuestionTag.tag_name == tag_name
            ).first()
            if not exists:
                new_tag = exam_model.UserQuestionTag(
                    user_id=self.user_id,
                    question_id=self.question.id,
                    tag_name=tag_name,
                    dirty=1
                )
                session.add(new_tag)
                session.commit()
        finally:
            session.close()

        self.new_tag_input.clear()
        self._load_tags()

        # Notify parent widget to refresh filter if necessary
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, "on_question_tag_changed"):
                parent_widget.on_question_tag_changed()
                break
            parent_widget = parent_widget.parent()

# ─────────────────────────────────────────────────────────────────────────────
# SelectTranscriptDialog — dialog to select transcript chunks for a question
# ─────────────────────────────────────────────────────────────────────────────
class SelectTranscriptDialog(QDialog):
    def __init__(self, exam_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Transcript Segment")
        self.resize(600, 400)
        self.exam_id = exam_id
        self.selected_chunks = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        desc = QLabel("Select one or more transcript lines to set the audio segment:")
        desc.setStyleSheet("font-size: 13px; color: #5f6368;")
        layout.addWidget(desc)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # Load chunks from DB
        session = get_session()
        try:
            self.chunks = session.query(exam_model.ExamSrtChunk).filter(
                exam_model.ExamSrtChunk.exam_id == self.exam_id
            ).order_by(exam_model.ExamSrtChunk.index.asc()).all()
            for chunk in self.chunks:
                item = QListWidgetItem(f"[{chunk.start_time:.2f}s – {chunk.end_time:.2f}s]  {chunk.text}")
                item.setData(Qt.ItemDataRole.UserRole, chunk)
                self.list_widget.addItem(item)
        finally:
            session.close()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #dadce0;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton:hover { background-color: #f1f3f4; }
        """)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("Save Segment")
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one transcript item.")
            return
            
        self.selected_chunks = sorted(
            [item.data(Qt.ItemDataRole.UserRole) for item in selected_items],
            key=lambda c: c.index
        )
        self.accept()

# ─────────────────────────────────────────────────────────────────────────────
# EditQuestionDialog — inline editor for a single ExamQuestion
# ─────────────────────────────────────────────────────────────────────────────
class EditQuestionDialog(QDialog):
    """Dialog that allows editing an ExamQuestion's core fields."""

    LETTERS = ["A", "B", "C", "D"]

    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question
        self.setWindowTitle(f"Edit Question {question.question_number}")
        self.resize(640, 520)
        self._build_ui()
        self._populate()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
                color: #3c4043;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #1a73e8;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #1a73e8;
                border: 1px solid #dadce0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton#save_btn {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton#save_btn:hover { background-color: #1558b0; }
            QPushButton#cancel_btn {
                background-color: white;
                color: #3c4043;
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton#cancel_btn:hover { background-color: #f1f3f4; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        header = QLabel(f"✏️  Editing  Q{self.question.question_number}")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        root.addWidget(header)

        # ── Meta row (Part + Correct Answer) ──────────────────────────────────
        meta_group = QGroupBox("Meta")
        meta_form = QFormLayout(meta_group)
        meta_form.setSpacing(8)

        self.part_combo = QComboBox()
        for p in range(1, 8):
            self.part_combo.addItem(f"Part {p}", p)
        meta_form.addRow("Part:", self.part_combo)

        self.answer_combo = QComboBox()
        for letter in self.LETTERS:
            self.answer_combo.addItem(letter)
        meta_form.addRow("Correct Answer:", self.answer_combo)
        root.addWidget(meta_group)

        # ── Content ───────────────────────────────────────────────────────────
        content_group = QGroupBox("Question Content")
        cg_layout = QVBoxLayout(content_group)
        self.content_edit = QTextEdit()
        self.content_edit.setFixedHeight(80)
        self.content_edit.setPlaceholderText("Enter question text here…")
        cg_layout.addWidget(self.content_edit)
        root.addWidget(content_group)

        # ── Options A–D ───────────────────────────────────────────────────────
        opts_group = QGroupBox("Options (A / B / C / D)")
        opts_form = QFormLayout(opts_group)
        opts_form.setSpacing(8)

        self.option_edits = []
        for letter in self.LETTERS:
            edit = QLineEdit()
            edit.setPlaceholderText(f"Option {letter}…")
            opts_form.addRow(f"{letter}:", edit)
            self.option_edits.append(edit)
        root.addWidget(opts_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("💾  Save Changes")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _populate(self):
        """Pre-fill form fields from the existing question."""
        q = self.question

        # Part
        idx = self.part_combo.findData(q.part)
        if idx >= 0:
            self.part_combo.setCurrentIndex(idx)

        # Correct answer
        ans_idx = self.answer_combo.findText(q.correct_answer or "A")
        if ans_idx >= 0:
            self.answer_combo.setCurrentIndex(ans_idx)

        # Content
        self.content_edit.setPlainText(q.content or "")

        # Options
        try:
            opts = json.loads(q.options) if isinstance(q.options, str) else (q.options or [])
        except Exception:
            opts = []
        for i, edit in enumerate(self.option_edits):
            edit.setText(opts[i] if i < len(opts) else "")

    # ── Save ──────────────────────────────────────────────────────────────────
    def _on_save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Validation", "Question content cannot be empty.")
            return

        options = [edit.text().strip() for edit in self.option_edits]
        if any(o == "" for o in options):
            QMessageBox.warning(self, "Validation", "All four options (A–D) must be filled in.")
            return

        session = get_session()
        try:
            db_q = session.query(exam_model.ExamQuestion).filter(
                exam_model.ExamQuestion.id == self.question.id
            ).first()
            if not db_q:
                QMessageBox.critical(self, "Error", "Question not found in database.")
                return

            db_q.part = self.part_combo.currentData()
            db_q.correct_answer = self.answer_combo.currentText()
            db_q.content = content
            db_q.options = options
            session.commit()

            # Reflect changes back onto the in-memory object so the caller
            # can refresh the list item without a full reload.
            self.question.part = db_q.part
            self.question.correct_answer = db_q.correct_answer
            self.question.content = db_q.content
            self.question.options = options

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error Saving", f"Could not save changes:\n{exc}")
            return
        finally:
            session.close()

        self.accept()


class OptionWidget(QWidget):
    """
    Renders shuffled multiple-choice options for one ExamQuestion.
    Anti-cheat: options are shuffled via enumerate + random.shuffle.
    Correct answer is validated by the original DB index, not display position.
    """
    LETTER_MAP = ["A", "B", "C", "D"]   # original DB order

    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question = question
        self.correct_answer = question.correct_answer   # e.g. "D"
        
        # Lấy index gốc của câu trả lời đúng (Ví dụ: "A" -> 0, "D" -> 3)
        try:
            self.orig_correct_idx = self.LETTER_MAP.index(self.correct_answer)
        except ValueError:
            self.orig_correct_idx = -1
            
        self.display_correct_letter = "" # Sẽ lưu chữ cái hiển thị thực tế của đáp án đúng
        self._build(question)

    def _build(self, q):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Header layout for question stem and tag button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Question stem
        stem = QLabel(f"<b>Q{q.question_number}.</b> {q.content}")
        stem.setWordWrap(True)
        stem.setStyleSheet("font-size: 13px; color: #202124; padding: 4px 0;")
        header_layout.addWidget(stem, stretch=1)

        # Bookmark/Tag button
        self.tag_btn = QPushButton()
        self.tag_btn.setIcon(qta.icon('fa5s.tags', color='#5f6368'))
        self.tag_btn.setToolTip("Manage tags for this question")
        self.tag_btn.setFixedSize(24, 24)
        self.tag_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                border-radius: 12px;
            }
        """)
        self.tag_btn.clicked.connect(self._show_tag_menu)
        header_layout.addWidget(self.tag_btn)

        # Select audio segment button
        self.select_audio_btn = QPushButton()
        self.select_audio_btn.setIcon(qta.icon('fa5s.music', color='#5f6368'))
        self.select_audio_btn.setToolTip("Select audio segment from transcript")
        self.select_audio_btn.setFixedSize(24, 24)
        self.select_audio_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                border-radius: 12px;
            }
        """)
        self.select_audio_btn.clicked.connect(self._on_select_audio_segment)
        header_layout.addWidget(self.select_audio_btn)

        layout.addLayout(header_layout)

        # Prepare options
        try:
            raw_opts = json.loads(q.options) if isinstance(q.options, str) else (q.options or [])
        except Exception:
            raw_opts = []

        # Bind original index (0=A, 1=B …) to each option text
        indexed = list(enumerate(raw_opts))
        random.shuffle(indexed)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for display_pos, (orig_idx, opt_text) in enumerate(indexed):
            display_letter = self.LETTER_MAP[display_pos] if display_pos < 4 else str(display_pos)
            
            # NẾU index gốc trùng với index của đáp án đúng -> Lưu lại chữ cái hiển thị mới này
            if orig_idx == self.orig_correct_idx:
                self.display_correct_letter = display_letter

            radio = QRadioButton(f"{display_letter}.  {opt_text}")
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 12px;
                    color: #3c4043;
                    padding: 3px 6px;
                }
                QRadioButton:hover { color: #1a73e8; }
            """)
            # Store the original DB index on the button
            radio.setProperty("orig_idx", orig_idx)
            self.btn_group.addButton(radio, display_pos)
            layout.addWidget(radio)

        self._result_label = QLabel("")
        self._result_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 2px 6px;")
        layout.addWidget(self._result_label)

        check_btn = QPushButton("Check Answer")
        check_btn.setFixedWidth(130)
        check_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        check_btn.clicked.connect(self._on_check)
        layout.addWidget(check_btn)

    def _on_check(self):
        selected = self.btn_group.checkedButton()
        if not selected:
            self._result_label.setText("⚠ Please select an option first.")
            self._result_label.setStyleSheet("color: #f9ab00; font-weight: bold; font-size: 12px;")
            return

        orig_idx = selected.property("orig_idx")

        # So sánh trực tiếp index gốc để chấm điểm chính xác tuyệt đối
        if orig_idx == self.orig_correct_idx:
            self._result_label.setText("✅ Correct!")
            self._result_label.setStyleSheet("color: #34a853; font-weight: bold; font-size: 12px;")
        else:
            # Khi sai, hiển thị chữ cái ĐANG XUẤT HIỆN trên màn hình (ví dụ: A) thay vì chữ cái trong DB (D)
            self._result_label.setText(f"❌ Wrong. Correct answer: {self.display_correct_letter}")
            self._result_label.setStyleSheet("color: #ea4335; font-weight: bold; font-size: 12px;")

    def _show_tag_menu(self):
        popup = TagMenuPopup(self.question, self)
        pos = self.tag_btn.mapToGlobal(QPoint(0, self.tag_btn.height()))
        popup.move(pos)
        popup.exec()

    def _on_select_audio_segment(self):
        dialog = SelectTranscriptDialog(self.question.exam_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_chunks:
            first = dialog.selected_chunks[0]
            last = dialog.selected_chunks[-1]
            
            session = get_session()
            try:
                db_q = session.query(exam_model.ExamQuestion).filter(
                    exam_model.ExamQuestion.id == self.question.id
                ).first()
                if db_q:
                    meta = dict(db_q.additional_meta or {})
                    meta["audio_start"] = first.start_time
                    meta["audio_end"] = last.end_time
                    db_q.additional_meta = meta
                    session.commit()
                    
                    self.question.additional_meta = meta
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error Saving", f"Could not save segment to database:\n{e}")
            finally:
                session.close()

            # Trigger a reload of details so the UI updates
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, "on_question_audio_changed"):
                    parent_widget.on_question_audio_changed(self.question)
                    break
                parent_widget = parent_widget.parent()




# ─────────────────────────────────────────────────────────────────────────────
# ExamGroupsWidget — main Groups & Questions tab
# ─────────────────────────────────────────────────────────────────────────────
class ExamGroupsWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel

        # Audio Player (for listening questions)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.positionChanged.connect(self._on_position_changed)

        self._audio_end_ms = 0        # current clip end in ms
        self._question_widgets = {}   # question_number → OptionWidget (for scroll navigation)

        self.setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        self.ui = Ui_ExamGroupsWidget()
        self.ui.setupUi(self)

        # Wire up references to widgets inside the loaded UI
        self.import_q_btn = self.ui.import_q_btn
        self.tag_filter_list = self.ui.tag_filter_list
        self.q_list = self.ui.q_list
        self.title_label = self.ui.title_label
        self.listen_widget = self.ui.listen_widget
        self.listen_btn = self.ui.listen_btn
        self.status_label = self.ui.status_label
        self.passage_label = self.ui.passage_label
        self.passage_browser = self.ui.passage_browser
        self.transcript_label = self.ui.transcript_label
        self.transcript_browser = self.ui.transcript_browser
        self.options_scroll = self.ui.options_scroll
        self.options_container = self.ui.options_container
        self.options_layout = self.ui.options_layout

        # Setup icons
        self.import_q_btn.setIcon(qta.icon('fa5s.file-import', color='#34a853'))
        self.listen_btn.setIcon(qta.icon('fa5s.play', color='white'))

        # Setup connections
        self.import_q_btn.clicked.connect(self._on_import_questions_clicked)
        self.tag_filter_list.itemChanged.connect(self._on_filter_changed)
        self.q_list.currentItemChanged.connect(self._on_question_selected)
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        self.passage_browser.anchorClicked.connect(self._on_passage_anchor_clicked)

        # Allow Ctrl/Shift multi-select so users can bulk-delete
        self.q_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Right-click context menu on the question list
        self.q_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.q_list.customContextMenuRequested.connect(self._on_q_list_context_menu)

    # ─────────────────────────────────────────────────────────────────────────
    # Public: populate from viewmodel
    # ─────────────────────────────────────────────────────────────────────────
    def populate(self):
        self.player.stop()
        self.populate_tags()
        self.q_list.clear()
        self._question_widgets.clear()
        self._clear_options()
        self.title_label.setText("Select a question to view details")
        self.listen_widget.setVisible(False)
        self.passage_label.setVisible(False)
        self.passage_browser.setVisible(False)
        self.transcript_label.setVisible(False)
        self.transcript_browser.setVisible(False)

        # Load audio source
        if self.viewmodel.exam and self.viewmodel.exam.full_audio_url:
            path = self.viewmodel.exam.full_audio_url
            if os.path.exists(path):
                self.player.setSource(QUrl.fromLocalFile(path))
            elif path.startswith("http"):
                self.player.setSource(QUrl(path))

        questions = getattr(self.viewmodel, 'questions', [])
        for q in questions:
            label = f"Q{q.question_number}  [Part {q.part}]  {q.content[:60]}…" \
                    if len(q.content) > 60 else f"Q{q.question_number}  [Part {q.part}]  {q.content}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, q)
            self.q_list.addItem(item)

    # ─────────────────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────────────────
    def _on_question_selected(self, current, previous):
        self.player.stop()
        self._clear_options()
        self.passage_label.setVisible(False)
        self.passage_browser.setVisible(False)
        self.transcript_label.setVisible(False)
        self.transcript_browser.setVisible(False)
        self.listen_widget.setVisible(False)

        if not current:
            return

        q = current.data(Qt.ItemDataRole.UserRole)
        self.title_label.setText(f"Part {q.part} — {q.content}")

        # ── Audio metadata ─────────────────────────────────────────────────
        audio_start, audio_end = _get_audio_meta(q)
        has_audio = audio_end > 0.0

        if has_audio:
            self._audio_end_ms = int(audio_end * 1000)
            self.status_label.setText(f"Segment: {audio_start:.2f}s – {audio_end:.2f}s")
            self.listen_widget.setVisible(True)

            # ── Transcript from SRT chunks ─────────────────────────────────
            self.transcript_label.setVisible(True)
            self.transcript_browser.setVisible(True)
            session = get_session()
            try:
                chunks = session.query(exam_model.ExamSrtChunk).filter(
                    exam_model.ExamSrtChunk.exam_id == self.viewmodel.exam_id,
                    exam_model.ExamSrtChunk.start_time >= audio_start,
                    exam_model.ExamSrtChunk.end_time <= audio_end
                ).order_by(exam_model.ExamSrtChunk.index.asc()).all()
                text = "\n".join(
                    f"[{c.start_time:.2f}s – {c.end_time:.2f}s]  {c.text}" for c in chunks
                )
                self.transcript_browser.setText(
                    text if text else "No matching transcript chunks found."
                )
            except Exception as exc:
                self.transcript_browser.setText(f"Error: {exc}")
            finally:
                session.close()

        # ── ExamContext rendering ──────────────────────────────────────────
        if q.context_id:
            session = get_session()
            try:
                ctx = session.query(exam_model.ExamContext).filter(
                    exam_model.ExamContext.id == q.context_id
                ).first()
                if ctx:
                    if ctx.context_type == "READING_PASSAGE":
                        self._render_reading_passage(ctx)
                    elif ctx.context_type == "AUDIO_SRT":
                        self._render_audio_srt_context(ctx)
            except Exception as exc:
                self.passage_browser.setPlainText(f"Error loading context: {exc}")
                self.passage_browser.setVisible(True)
            finally:
                session.close()

        # ── Build shuffled option widgets for this question ────────────────
        # Load all questions that share the same context (e.g. a passage group)
        questions = getattr(self.viewmodel, 'questions', [])
        group = [x for x in questions if x.context_id == q.context_id] if q.context_id else [q]

        for gq in group:
            opt_w = OptionWidget(gq)
            self._question_widgets[gq.question_number] = opt_w
            # Insert before the trailing stretch
            count = self.options_layout.count()
            self.options_layout.insertWidget(count - 1, opt_w)

        # Scroll to the selected question
        if q.question_number in self._question_widgets:
            target = self._question_widgets[q.question_number]
            def _safe_scroll(w=target):
                try:
                    self.options_scroll.ensureWidgetVisible(w)
                except RuntimeError:
                    pass  # C++ object already deleted – ignore
            QTimer.singleShot(50, _safe_scroll)

    def _on_listen_clicked(self):
        item = self.q_list.currentItem()
        if not item:
            return
        q = item.data(Qt.ItemDataRole.UserRole)
        audio_start, audio_end = _get_audio_meta(q)
        self._audio_end_ms = int(audio_end * 1000)
        self.player.setPosition(int(audio_start * 1000))
        self.player.play()

    def _on_position_changed(self, pos_ms):
        """Pause automatically when the clip end is reached."""
        if (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                and self._audio_end_ms > 0
                and pos_ms >= self._audio_end_ms):
            self.player.pause()

    def _on_passage_anchor_clicked(self, url):
        """
        Called when the user clicks [[N]] anchor in the reading passage.
        Scrolls the matching OptionWidget into view, or shows an inline QMenu.
        """
        q_num_str = url.toString()
        try:
            q_num = int(q_num_str)
        except ValueError:
            return

        target = self._question_widgets.get(q_num)
        if target:
            self.options_scroll.ensureWidgetVisible(target)
        else:
            # Show a quick informational popup at cursor
            menu = QMenu(self)
            menu.addAction(f"Question {q_num} not in current view")
            menu.exec(QCursor.pos())

    # ─────────────────────────────────────────────────────────────────────────
    # Edit / Delete question
    # ─────────────────────────────────────────────────────────────────────────
    def _on_q_list_context_menu(self, pos: QPoint):
        """Show Edit / Delete context menu for the right-clicked list item."""
        clicked_item = self.q_list.itemAt(pos)
        if not clicked_item:
            return

        # Make sure the clicked item is part of the selection; if the user
        # right-clicked on an unselected item select only that one.
        selected_items = self.q_list.selectedItems()
        if clicked_item not in selected_items:
            self.q_list.clearSelection()
            clicked_item.setSelected(True)
            selected_items = [clicked_item]

        n = len(selected_items)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                font-size: 12px;
                color: #202124;
            }
            QMenu::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
                border-radius: 4px;
            }
            QMenu::separator { height: 1px; background: #dadce0; margin: 4px 8px; }
        """)

        # Edit is only available when exactly one question is selected
        edit_action = None
        if n == 1:
            edit_action = menu.addAction(qta.icon('fa5s.edit', color='#1a73e8'), "Edit Question")
            menu.addSeparator()

        delete_label = f"Delete {n} Questions" if n > 1 else "Delete Question"
        delete_action = menu.addAction(qta.icon('fa5s.trash-alt', color='#ea4335'), delete_label)

        action = menu.exec(self.q_list.viewport().mapToGlobal(pos))

        if edit_action and action == edit_action:
            self._on_edit_question(clicked_item)
        elif action == delete_action:
            self._on_delete_questions(selected_items)

    def _on_edit_question(self, item: QListWidgetItem):
        """Open EditQuestionDialog for the given list item."""
        q = item.data(Qt.ItemDataRole.UserRole)
        dialog = EditQuestionDialog(q, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Update list item label to reflect new content
        updated_q = dialog.question
        label = (
            f"Q{updated_q.question_number}  [Part {updated_q.part}]  "
            f"{updated_q.content[:60]}…"
            if len(updated_q.content) > 60
            else f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content}"
        )
        item.setText(label)
        item.setData(Qt.ItemDataRole.UserRole, updated_q)

        # If this item is currently selected, refresh the detail panel
        if self.q_list.currentItem() is item:
            self._on_question_selected(item, None)

        QMessageBox.information(self, "Saved", "Question updated successfully.")

    def _on_delete_questions(self, items: list):
        """Confirm and permanently delete one or more questions from the database."""
        n = len(items)
        if n == 1:
            q = items[0].data(Qt.ItemDataRole.UserRole)
            msg = (
                f"Are you sure you want to permanently delete Q{q.question_number}?\n"
                "This action cannot be undone."
            )
        else:
            nums = ", ".join(
                f"Q{it.data(Qt.ItemDataRole.UserRole).question_number}" for it in items
            )
            msg = (
                f"Are you sure you want to permanently delete {n} questions?\n"
                f"{nums}\n\nThis action cannot be undone."
            )

        reply = QMessageBox.question(
            self,
            "Delete Question" if n == 1 else f"Delete {n} Questions",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ids_to_delete = [it.data(Qt.ItemDataRole.UserRole).id for it in items]

        session = get_session()
        try:
            session.query(exam_model.ExamQuestion).filter(
                exam_model.ExamQuestion.id.in_(ids_to_delete)
            ).delete(synchronize_session="fetch")
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete questions:\n{exc}")
            return
        finally:
            session.close()

        # Remove all deleted items from the list (iterate in reverse to keep indices stable)
        self.q_list.blockSignals(True)
        for item in items:
            row = self.q_list.row(item)
            self.q_list.takeItem(row)
        self.q_list.blockSignals(False)

        # Clear detail panel if nothing is selected anymore
        if self.q_list.currentItem() is None:
            self._clear_options()
            self.title_label.setText("Select a question to view details")
            self.listen_widget.setVisible(False)
            self.passage_label.setVisible(False)
            self.passage_browser.setVisible(False)
            self.transcript_label.setVisible(False)
            self.transcript_browser.setVisible(False)

    def _on_import_questions_clicked(self):
        dialog = ImportQuestionsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        contexts_data = dialog.result_contexts   # list[dict] with 'llm_id' key
        questions_data = dialog.result_questions  # list[dict] with 'llm_context_id' key
        if not questions_data:
            return

        session = get_session()
        try:
            # ── Step 1: Insert ExamContext rows & build llm_id → real DB uuid map ──
            llm_to_real_id: dict[str, str] = {}
            for ctx_data in contexts_data:
                llm_id = ctx_data.get("llm_id", "")
                new_ctx = exam_model.ExamContext(
                    exam_id=self.viewmodel.exam_id,
                    context_type=ctx_data.get("context_type", "READING_PASSAGE"),
                    content=ctx_data.get("content", {}),
                    index=ctx_data.get("index", 0),
                )
                session.add(new_ctx)
                session.flush()  # populate new_ctx.id without full commit
                if llm_id:
                    llm_to_real_id[llm_id] = new_ctx.id

            # ── Step 2: Insert ExamQuestion rows with resolved context_id ──────────
            for idx, q_data in enumerate(questions_data):
                # Resolve the LLM's temporary context reference to the real DB uuid
                llm_ctx_id = q_data.get("llm_context_id")
                real_ctx_id = llm_to_real_id.get(llm_ctx_id) if llm_ctx_id else None

                # additional_meta is already a dict from the parser
                additional_meta = q_data.get("additional_meta") or {
                    "audio_start": 0.0,
                    "audio_end":   0.0,
                }

                new_q = exam_model.ExamQuestion(
                    exam_id=self.viewmodel.exam_id,
                    context_id=real_ctx_id,
                    part=int(q_data.get("part", 1)),
                    question_number=int(q_data.get("question_number", idx + 1)),
                    question_type=q_data.get("question_type", "MULTIPLE_CHOICE"),
                    content=q_data["content"],
                    options=q_data["options"],
                    correct_answer=q_data.get("correct_answer", ""),
                    additional_meta=additional_meta,
                )
                session.add(new_q)

            session.commit()
            n_ctx = len(contexts_data)
            n_q   = len(questions_data)
            QMessageBox.information(
                self, "Import Successful",
                f"Imported {n_ctx} context(s) and {n_q} question(s) successfully!"
            )
            self.viewmodel.load_exam()
            self.populate()

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self, "Error Saving Import",
                f"Could not save to database.\nDetails: {exc}"
            )
        finally:
            session.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Context renderers
    # ─────────────────────────────────────────────────────────────────────────
    def _render_reading_passage(self, ctx):
        """
        Parse READING_PASSAGE content and render double-bracket placeholders
        [[131]] → clickable anchor tags, per spec §4.
        """
        if isinstance(ctx.content, dict):
            raw = ctx.content.get("text", "")
        else:
            raw = str(ctx.content or "")

        def replace_placeholder(m):
            num = m.group(1)
            return (
                f'<a href="{num}" style="text-decoration:none; color:#0078d4;">'
                f'({num}) ________</a>'
            )

        html_content = re.sub(r'\[\[(\d+)\]\]', replace_placeholder, raw)
        html_content = html_content.replace("\n", "<br>")

        self.passage_browser.setHtml(
            f'<div style="font-family: Georgia, serif; font-size:13px; '
            f'line-height:1.8; color:#202124;">{html_content}</div>'
        )
        self.passage_label.setVisible(True)
        self.passage_browser.setVisible(True)

    def _render_audio_srt_context(self, ctx):
        """Display AUDIO_SRT context as a readable transcript."""
        try:
            entries = ctx.content if isinstance(ctx.content, list) else json.loads(ctx.content)
            lines = [
                f"[{e.get('start', 0):.2f}s – {e.get('end', 0):.2f}s]  {e.get('text', '')}"
                for e in entries
            ]
            self.transcript_browser.setText("\n".join(lines))
            self.transcript_label.setVisible(True)
            self.transcript_browser.setVisible(True)
        except Exception as exc:
            self.transcript_browser.setText(f"Error reading audio context: {exc}")
            self.transcript_browser.setVisible(True)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _clear_options(self):
        """Remove all OptionWidget children from the scrollable layout."""
        while self.options_layout.count() > 1:   # keep trailing stretch
            item = self.options_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                del item
        self._question_widgets.clear()

    def populate_tags(self):
        self.tag_filter_list.blockSignals(True)
        checked_tags = set()
        for i in range(self.tag_filter_list.count()):
            item = self.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_tags.add(item.text())

        self.tag_filter_list.clear()
        
        session = get_session()
        try:
            all_tags_rows = session.query(exam_model.UserQuestionTag.tag_name).filter(
                exam_model.UserQuestionTag.user_id == "local_user"
            ).distinct().all()
            all_tags = sorted([r[0] for r in all_tags_rows])
            
            for tag_name in all_tags:
                item = QListWidgetItem(tag_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if tag_name in checked_tags:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.tag_filter_list.addItem(item)
        finally:
            session.close()
            
        self.tag_filter_list.blockSignals(False)

    def _on_filter_changed(self):
        selected_tags = []
        for i in range(self.tag_filter_list.count()):
            item = self.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tags.append(item.text())

        self.q_list.blockSignals(True)
        self.q_list.clear()
        self._clear_options()

        session = get_session()
        try:
            if not selected_tags:
                questions = session.query(exam_model.ExamQuestion).filter(
                    exam_model.ExamQuestion.exam_id == self.viewmodel.exam_id
                ).order_by(exam_model.ExamQuestion.question_number.asc()).all()
            else:
                questions = session.query(exam_model.ExamQuestion).join(
                    exam_model.UserQuestionTag,
                    exam_model.ExamQuestion.id == exam_model.UserQuestionTag.question_id
                ).filter(
                    exam_model.ExamQuestion.exam_id == self.viewmodel.exam_id,
                    exam_model.UserQuestionTag.user_id == "local_user",
                    exam_model.UserQuestionTag.tag_name.in_(selected_tags)
                ).distinct().order_by(exam_model.ExamQuestion.question_number.asc()).all()

            for q in questions:
                label = f"Q{q.question_number}  [Part {q.part}]  {q.content[:60]}…" \
                        if len(q.content) > 60 else f"Q{q.question_number}  [Part {q.part}]  {q.content}"
                item = QListWidgetItem(label)
                session.expunge(q)
                item.setData(Qt.ItemDataRole.UserRole, q)
                self.q_list.addItem(item)
        finally:
            session.close()

        self.q_list.blockSignals(False)
        self.title_label.setText("Select a question to view details")

    def on_question_tag_changed(self):
        self.populate_tags()
        self._on_filter_changed()

    def on_question_audio_changed(self, question):
        current_item = self.q_list.currentItem()
        if current_item:
            q = current_item.data(Qt.ItemDataRole.UserRole)
            if q.id == question.id:
                q.additional_meta = question.additional_meta
                current_item.setData(Qt.ItemDataRole.UserRole, q)
                self._on_question_selected(current_item, None)


    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
