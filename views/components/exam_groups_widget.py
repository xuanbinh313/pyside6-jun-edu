import json
import os
import re
import random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTextBrowser, QScrollArea,
    QMessageBox, QDialog, QFrame, QButtonGroup, QRadioButton,
    QSizePolicy, QMenu, QCheckBox, QLineEdit, QAbstractItemView
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QPalette, QCursor

import qtawesome as qta
from models.database import get_session
from views.components.import_questions_dialog import ImportQuestionsDialog
import models.exam as exam_model


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
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
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
            if item.widget():
                item.widget().deleteLater()

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
            if state == Qt.Checked.value:
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
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
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
                item.setData(Qt.UserRole, chunk)
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
            [item.data(Qt.UserRole) for item in selected_items],
            key=lambda c: c.index
        )
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
        self.correct_answer = question.correct_answer   # e.g. "A"
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
        # Convert original index → letter (0→A, 1→B …)
        selected_letter = self.LETTER_MAP[orig_idx] if orig_idx < 4 else str(orig_idx)

        if selected_letter == self.correct_answer:
            self._result_label.setText("✅ Correct!")
            self._result_label.setStyleSheet("color: #34a853; font-weight: bold; font-size: 12px;")
        else:
            self._result_label.setText(f"❌ Wrong. Correct answer: {self.correct_answer}")
            self._result_label.setStyleSheet("color: #ea4335; font-weight: bold; font-size: 12px;")

    def _show_tag_menu(self):
        popup = TagMenuPopup(self.question, self)
        pos = self.tag_btn.mapToGlobal(QPoint(0, self.tag_btn.height()))
        popup.move(pos)
        popup.exec()

    def _on_select_audio_segment(self):
        dialog = SelectTranscriptDialog(self.question.exam_id, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_chunks:
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
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # ── Left panel: question list ──────────────────────────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        q_label_layout = QHBoxLayout()
        q_label = QLabel("Exam Questions")
        q_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a73e8;")
        q_label_layout.addWidget(q_label)
        q_label_layout.addStretch()

        self.import_q_btn = QPushButton()
        self.import_q_btn.setIcon(qta.icon('fa5s.file-import', color='#34a853'))
        self.import_q_btn.setToolTip("Import Questions from CSV")
        self.import_q_btn.setFixedSize(28, 28)
        self.import_q_btn.clicked.connect(self._on_import_questions_clicked)
        q_label_layout.addWidget(self.import_q_btn)

        left_layout.addLayout(q_label_layout)

        # Tag Filter block
        filter_label = QLabel("Filter by Tags:")
        filter_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #5f6368; margin-top: 4px;")
        left_layout.addWidget(filter_label)

        self.tag_filter_list = QListWidget()
        self.tag_filter_list.setMaximumHeight(80)
        self.tag_filter_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #f8f9fa;
                padding: 2px;
            }
            QListWidget::item {
                padding: 4px;
            }
        """)
        self.tag_filter_list.itemChanged.connect(self._on_filter_changed)
        left_layout.addWidget(self.tag_filter_list)

        self.q_list = QListWidget()
        self.q_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #ffffff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f1f3f4;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
                font-weight: bold;
                border-radius: 4px;
            }
        """)
        self.q_list.currentItemChanged.connect(self._on_question_selected)
        left_layout.addWidget(self.q_list)

        main_layout.addWidget(left_panel, stretch=2)

        # ── Right panel: context + options (scrollable) ────────────────────
        right_outer = QWidget()
        right_outer_layout = QVBoxLayout(right_outer)
        right_outer_layout.setContentsMargins(0, 0, 0, 0)
        right_outer_layout.setSpacing(8)

        self.title_label = QLabel("Select a question to view details")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3c4043;")
        self.title_label.setWordWrap(True)
        right_outer_layout.addWidget(self.title_label)

        # Listening panel
        self.listen_widget = QWidget()
        self.listen_widget.setVisible(False)
        listen_sub = QHBoxLayout(self.listen_widget)
        listen_sub.setContentsMargins(0, 5, 0, 5)

        self.listen_btn = QPushButton("Listen to this segment")
        self.listen_btn.setIcon(qta.icon('fa5s.play', color='white'))
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white;
                font-weight: bold; padding: 8px 16px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        listen_sub.addWidget(self.listen_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #5f6368; font-style: italic; font-size: 12px;")
        listen_sub.addWidget(self.status_label)
        listen_sub.addStretch()
        right_outer_layout.addWidget(self.listen_widget)

        # Reading passage context (READING_PASSAGE)
        self.passage_label = QLabel("Reading Passage")
        self.passage_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a73e8;")
        self.passage_label.setVisible(False)
        right_outer_layout.addWidget(self.passage_label)

        self.passage_browser = QTextBrowser()
        self.passage_browser.setOpenLinks(False)
        self.passage_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #dadce0; border-radius: 6px;
                background-color: #fffde7; padding: 10px;
                font-size: 13px; line-height: 1.6;
            }
        """)
        self.passage_browser.setVisible(False)
        self.passage_browser.anchorClicked.connect(self._on_passage_anchor_clicked)
        right_outer_layout.addWidget(self.passage_browser)

        # Transcript context (AUDIO_SRT)
        self.transcript_label = QLabel("Transcript Context")
        self.transcript_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a73e8;")
        self.transcript_label.setVisible(False)
        right_outer_layout.addWidget(self.transcript_label)

        self.transcript_browser = QTextBrowser()
        self.transcript_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #dadce0; border-radius: 6px;
                background-color: #ffffff; padding: 10px;
                font-size: 13px; line-height: 1.5;
            }
        """)
        self.transcript_browser.setVisible(False)
        right_outer_layout.addWidget(self.transcript_browser)

        # Scrollable area for option widgets
        self.options_scroll = QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_scroll.setStyleSheet("QScrollArea { border: none; }")

        self.options_container = QWidget()
        self.options_layout = QVBoxLayout(self.options_container)
        self.options_layout.setContentsMargins(4, 4, 4, 4)
        self.options_layout.setSpacing(12)
        self.options_layout.addStretch()
        self.options_scroll.setWidget(self.options_container)
        right_outer_layout.addWidget(self.options_scroll, stretch=1)

        main_layout.addWidget(right_outer, stretch=3)

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
            item.setData(Qt.UserRole, q)
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

        q = current.data(Qt.UserRole)
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
            QTimer.singleShot(50, lambda: self.options_scroll.ensureWidgetVisible(target))

    def _on_listen_clicked(self):
        item = self.q_list.currentItem()
        if not item:
            return
        q = item.data(Qt.UserRole)
        audio_start, audio_end = _get_audio_meta(q)
        self._audio_end_ms = int(audio_end * 1000)
        self.player.setPosition(int(audio_start * 1000))
        self.player.play()

    def _on_position_changed(self, pos_ms):
        """Pause automatically when the clip end is reached."""
        if (self.player.playbackState() == QMediaPlayer.PlayingState
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

    def _on_import_questions_clicked(self):
        dialog = ImportQuestionsDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        questions_data = dialog.result_questions
        if not questions_data:
            return

        session = get_session()
        try:
            for idx, q_data in enumerate(questions_data):
                meta = {
                    "audio_start": q_data.get("audio_start", 0.0),
                    "audio_end":   q_data.get("audio_end",   0.0),
                }
                new_q = exam_model.ExamQuestion(
                    exam_id=self.viewmodel.exam_id,
                    context_id=q_data.get("context_id") or None,
                    part=int(q_data.get("part", 1)),
                    question_number=int(q_data.get("question_number", idx + 1)),
                    question_type=q_data.get("question_type", "MULTIPLE_CHOICE"),
                    content=q_data["content"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    additional_meta=meta,
                )
                session.add(new_q)

            session.commit()
            QMessageBox.information(
                self, "Success",
                f"Successfully imported {len(questions_data)} questions!"
            )
            self.viewmodel.load_exam()
            self.populate()

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self, "Error Saving Questions",
                f"Could not save questions to database.\nDetails: {exc}"
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
        raw = ctx.content if isinstance(ctx.content, str) else json.dumps(ctx.content)

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
            if item.widget():
                item.widget().deleteLater()
        self._question_widgets.clear()

    def populate_tags(self):
        self.tag_filter_list.blockSignals(True)
        checked_tags = set()
        for i in range(self.tag_filter_list.count()):
            item = self.tag_filter_list.item(i)
            if item.checkState() == Qt.Checked:
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
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if tag_name in checked_tags:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.tag_filter_list.addItem(item)
        finally:
            session.close()
            
        self.tag_filter_list.blockSignals(False)

    def _on_filter_changed(self):
        selected_tags = []
        for i in range(self.tag_filter_list.count()):
            item = self.tag_filter_list.item(i)
            if item.checkState() == Qt.Checked:
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
                item.setData(Qt.UserRole, q)
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
            q = current_item.data(Qt.UserRole)
            if q.id == question.id:
                q.additional_meta = question.additional_meta
                current_item.setData(Qt.UserRole, q)
                self._on_question_selected(current_item, None)


    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
