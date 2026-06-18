import json
import random

import qtawesome as qta
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (QButtonGroup, QDialog, QMessageBox, QPushButton,
                               QRadioButton, QWidget)

import src.models.exam as exam_model
from src.models.database import get_session
from src.utils.helpers import get_audio_meta
from src.views.components.edit_question_dialog import EditQuestionDialog
from src.views.components.select_transcript_dialog import \
    SelectTranscriptDialog
from src.views.components.tag_menu_dialog import TagMenuDialog

from .ui_option_question_item import Ui_OptionQuestionItem

# ─────────────────────────────────────────────────────────────────────────────
# OptionQuestionItem — shuffled ABCD radio buttons for a single question
# ─────────────────────────────────────────────────────────────────────────────

class OptionQuestionItem(QWidget):
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
        self.ui = Ui_OptionQuestionItem()
        self.ui.setupUi(self)

        # Question stem text & stretch factor
        self.ui.stem.setText(f"<b>Q{q.question_number}.</b> {q.content}")
        self.ui.stem.setStyleSheet("font-size: 13px; color: #202124; padding: 4px 0;")
        self.ui.header_layout.setStretchFactor(self.ui.stem, 1)

        _icon_btn_style = """
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                border-radius: 12px;
            }
        """

        # Edit question button setup
        self.ui.edit_q_btn.setIcon(qta.icon('fa5s.edit', color='#1a73e8'))
        self.ui.edit_q_btn.setToolTip("Edit this question")
        self.ui.edit_q_btn.setFixedSize(24, 24)
        self.ui.edit_q_btn.setStyleSheet(_icon_btn_style)
        self.ui.edit_q_btn.clicked.connect(self._on_edit_question)

        # Bookmark/Tag button setup
        self.ui.tag_btn.setIcon(qta.icon('fa5s.tags', color='#5f6368'))
        self.ui.tag_btn.setToolTip("Manage tags for this question")
        self.ui.tag_btn.setFixedSize(24, 24)
        self.ui.tag_btn.setStyleSheet(_icon_btn_style)
        self.ui.tag_btn.clicked.connect(self._show_tag_menu)

        # Select audio segment button setup
        self.ui.select_audio_btn.setIcon(qta.icon('fa5s.music', color='#5f6368'))
        self.ui.select_audio_btn.setToolTip("Select audio segment from transcript")
        self.ui.select_audio_btn.setFixedSize(24, 24)
        self.ui.select_audio_btn.setStyleSheet(_icon_btn_style)
        self.ui.select_audio_btn.clicked.connect(self._on_select_audio_segment)

        self.play_audio_btn = None
        self.update_audio_ui()

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
            self.ui.options_layout.addWidget(radio)

        self._result_label = self.ui.result_label
        self._result_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 2px 6px;")

        self.ui.check_btn.setFixedWidth(130)
        self.ui.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #1558b0; }
        """)
        self.ui.check_btn.clicked.connect(self._on_check)

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

    def update_audio_ui(self):
        # Remove old play button if it exists
        if hasattr(self, 'play_audio_btn') and self.play_audio_btn is not None:
            try:
                self.play_audio_btn.deleteLater()
            except RuntimeError:
                pass
            self.play_audio_btn = None
        
        # Build play button if it has audio segment
        audio_start, audio_end = get_audio_meta(self.question)
        if audio_end > 0.0:
            self.play_audio_btn = QPushButton()
            self.play_audio_btn.setIcon(qta.icon('fa5s.play', color='#34a853'))
            self.play_audio_btn.setToolTip(f"Play segment: {audio_start:.2f}s – {audio_end:.2f}s")
            self.play_audio_btn.setFixedSize(24, 24)
            
            _icon_btn_style = """
                QPushButton {
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #f1f3f4;
                    border-radius: 12px;
                }
            """
            self.play_audio_btn.setStyleSheet(_icon_btn_style)
            self.play_audio_btn.clicked.connect(self._on_play_audio)
            
            # Insert it before select_audio_btn
            idx = self.ui.header_layout.indexOf(self.ui.select_audio_btn)
            self.ui.header_layout.insertWidget(idx, self.play_audio_btn)
                

    def _on_play_audio(self):
        # Find parent ExamGroupsWidget
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'player') and hasattr(parent_widget, 'audio_output'):
                # Set player position and play
                audio_start, audio_end = get_audio_meta(self.question)
                setattr(parent_widget, '_audio_end_ms', int(audio_end * 1000))
                parent_widget.player.setPosition(int(audio_start * 1000))  # type: ignore
                parent_widget.player.play()  # type: ignore
                break
            parent_widget = parent_widget.parent()

    def _on_edit_question(self):
        dialog = EditQuestionDialog(self.question, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        # Refresh the stem label with updated content
        updated_q = dialog.question
        self.question = updated_q
        self.ui.stem.setText(f"<b>Q{updated_q.question_number}.</b> {updated_q.content}")
        # Notify parent to refresh list item label
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'on_question_edited'):
                parent_widget.on_question_edited(updated_q)
                break
            parent_widget = parent_widget.parent()

    def _show_tag_menu(self):
        popup = TagMenuDialog(self.question, self)
        pos = self.ui.tag_btn.mapToGlobal(QPoint(0, self.ui.tag_btn.height()))
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