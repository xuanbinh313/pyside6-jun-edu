import html
from typing import Optional, Protocol, Sequence

import qtawesome as qta
from diff_match_patch import diff_match_patch
from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.utils.helpers import get_local_media_path


class DictationChunk(Protocol):
    index: int
    start_time: float
    end_time: float
    text: str


class DictationInput(QTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        modifiers = event.modifiers()
        submit_modifiers = (
            Qt.KeyboardModifier.ShiftModifier
            | Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
        )
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not modifiers & submit_modifiers
        ):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ExerciseDictationView(QWidget):
    def __init__(
        self,
        chunks: Sequence[DictationChunk],
        audio_name: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._chunks = list(chunks)
        self._audio_name = audio_name
        self._current_index = 0
        self._clip_end_ms = 0
        self._last_expected_text = ""
        self._last_typed_text = ""
        self._has_checked_answer = False
        self._answer_revealed = False

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_position_changed)

        self._build_ui()
        self._load_audio()
        self._render_current_chunk()

    def start(self) -> None:
        self._current_index = 0
        self._render_current_chunk()
        self.play_current()

    def stop(self) -> None:
        self.player.stop()

    def play_current(self) -> None:
        chunk = self._current_chunk()
        if chunk is None:
            return
        self._clip_end_ms = int(chunk.end_time * 1000)
        self.player.setPosition(int(chunk.start_time * 1000))
        self.player.play()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header.setStyleSheet(
            "QFrame { background: #ffffff; border-radius: 6px; }"
            "QLabel { color: #202124; }"
        )
        header_layout = QHBoxLayout(header)

        self.title_label = QLabel("Dictation")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label, 1)

        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(qta.icon("fa5s.chevron-left", color="#3c4043"))
        self.prev_btn.setIconSize(QSize(16, 16))
        self.prev_btn.setToolTip("Previous transcript")
        self.prev_btn.clicked.connect(self._previous_chunk)
        header_layout.addWidget(self.prev_btn)

        self.position_label = QLabel("0 / 0")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.position_label)

        self.next_btn = QPushButton()
        self.next_btn.setIcon(qta.icon("fa5s.chevron-right", color="#3c4043"))
        self.next_btn.setIconSize(QSize(16, 16))
        self.next_btn.setToolTip("Next transcript")
        self.next_btn.clicked.connect(self._next_chunk)
        header_layout.addWidget(self.next_btn)
        layout.addWidget(header)

        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #5f6368;")
        layout.addWidget(self.time_label)

        self.play_btn = QPushButton("Play")
        self.play_btn.setIcon(qta.icon("fa5s.play", color="white"))
        self.play_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; "
            "font-weight: bold; border-radius: 4px; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #1558b0; }"
            "QPushButton:disabled { background-color: #dadce0; color: #5f6368; }"
        )
        self.play_btn.clicked.connect(self.play_current)
        layout.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(16)

        self.show_answer_immediately_check = QCheckBox("Show answer immediately")
        self.show_answer_immediately_check.setChecked(True)
        # self.show_answer_immediately_check.setStyleSheet("color: #3c4043;")
        self.show_answer_immediately_check.toggled.connect(
            self._on_show_answer_immediately_changed
        )
        options_layout.addWidget(self.show_answer_immediately_check)

        self.show_full_answer_check = QCheckBox("Show full answer")
        self.show_full_answer_check.setChecked(True)
        # self.show_full_answer_check.setStyleSheet("color: #3c4043;")
        self.show_full_answer_check.toggled.connect(self._on_show_full_answer_changed)
        options_layout.addWidget(self.show_full_answer_check)
        options_layout.addStretch(1)
        layout.addLayout(options_layout)

        prompt = QLabel("Type what you hear")
        prompt.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(prompt)

        self.input_edit = DictationInput()
        self.input_edit.setAcceptRichText(False)
        self.input_edit.setPlaceholderText("Press Enter to check. Shift+Enter adds a new line.")
        self.input_edit.setMinimumHeight(120)
        self.input_edit.submitted.connect(self._check_answer)
        layout.addWidget(self.input_edit)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

        self.show_answer_btn = QPushButton("Show Answer")
        self.show_answer_btn.setIcon(qta.icon("fa5s.eye", color="#1a73e8"))
        self.show_answer_btn.setStyleSheet(
            "QPushButton { color: #1a73e8; background: #ffffff; "
            "border: 1px solid #d2e3fc; border-radius: 4px; padding: 7px 14px; }"
            "QPushButton:hover { background: #e8f0fe; }"
        )
        self.show_answer_btn.clicked.connect(self._show_answer)
        self.show_answer_btn.hide()
        layout.addWidget(self.show_answer_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setMinimumHeight(140)
        self.diff_view.setStyleSheet(
            "QTextEdit { background: #ffffff; border: 1px solid #dadce0; "
            "border-radius: 6px; padding: 8px; }"
        )
        layout.addWidget(self.diff_view, 1)

    def _load_audio(self) -> None:
        if not self._audio_name:
            return
        path = get_local_media_path(self._audio_name)
        if path.exists():
            self.player.setSource(QUrl.fromLocalFile(str(path)))

    def _render_current_chunk(self) -> None:
        chunk = self._current_chunk()
        count = len(self._chunks)
        self.position_label.setText(f"{self._current_index + 1 if chunk else 0} / {count}")

        if chunk is None:
            self.time_label.setText("No transcript chunks are available.")
            self.input_edit.setEnabled(False)
            self.play_btn.setEnabled(False)
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        self.input_edit.setEnabled(True)
        self.play_btn.setEnabled(bool(self._audio_name))
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < count - 1)
        self.time_label.setText(
            f"Chunk {chunk.index}: {chunk.start_time:.3f}s - {chunk.end_time:.3f}s"
        )
        self.input_edit.clear()
        self.diff_view.clear()
        self.status_label.clear()
        self.show_answer_btn.hide()
        self._last_expected_text = ""
        self._last_typed_text = ""
        self._has_checked_answer = False
        self._answer_revealed = False
        self.input_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def _current_chunk(self) -> Optional[DictationChunk]:
        if not self._chunks:
            return None
        if self._current_index < 0 or self._current_index >= len(self._chunks):
            return None
        return self._chunks[self._current_index]

    def _previous_chunk(self) -> None:
        if self._current_index <= 0:
            return
        self.player.pause()
        self._current_index -= 1
        self._render_current_chunk()
        self.play_current()

    def _next_chunk(self) -> None:
        if self._current_index >= len(self._chunks) - 1:
            return
        self.player.pause()
        self._current_index += 1
        self._render_current_chunk()
        self.play_current()

    def _check_answer(self) -> None:
        chunk = self._current_chunk()
        if chunk is None:
            return
        typed_text = self.input_edit.toPlainText()
        expected_text = chunk.text or ""
        self._last_expected_text = expected_text
        self._last_typed_text = typed_text
        self._has_checked_answer = True
        self._answer_revealed = False
        is_correct = self._normalize_for_check(typed_text) == self._normalize_for_check(
            expected_text
        )
        if is_correct:
            self.status_label.setText("Correct!")
            self.status_label.setStyleSheet("font-weight: bold; color: #188038;")
        else:
            self.status_label.setText("Incorrect")
            self.status_label.setStyleSheet("font-weight: bold; color: #d93025;")
        if self.show_answer_immediately_check.isChecked():
            self._show_answer()
            return
        self.diff_view.clear()
        self.show_answer_btn.show()

    def _show_answer(self) -> None:
        self._answer_revealed = True
        self.show_answer_btn.hide()
        self.diff_view.setHtml(
            self._diff_html(
                self._last_expected_text,
                self._last_typed_text,
                self.show_full_answer_check.isChecked(),
            )
        )

    def _on_show_answer_immediately_changed(self, checked: bool) -> None:
        if not self._has_checked_answer:
            return
        if checked:
            self._show_answer()
            return
        self._answer_revealed = False
        self.diff_view.clear()
        self.show_answer_btn.show()

    def _on_show_full_answer_changed(self, checked: bool) -> None:
        if not self._has_checked_answer or not self._answer_revealed:
            return
        self.diff_view.setHtml(
            self._diff_html(
                self._last_expected_text,
                self._last_typed_text,
                checked,
            )
        )

    def _on_position_changed(self, position_ms: int) -> None:
        if (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            and self._clip_end_ms > 0
            and position_ms >= self._clip_end_ms
        ):
            self.player.pause()

    @staticmethod
    def _normalize_for_check(text: str) -> str:
        normalized = "".join(
            char.lower() for char in text if char.isalnum() or char.isspace()
        )
        return " ".join(normalized.split())

    @staticmethod
    def _diff_html(expected_text: str, typed_text: str, show_full_answer: bool) -> str:
        differ = diff_match_patch()
        diffs = differ.diff_main(expected_text, typed_text)
        differ.diff_cleanupSemantic(diffs)

        fragments = []
        for op, text in diffs:
            display_text = (
                text
                if show_full_answer or op > 0
                else ExerciseDictationView._mask_answer_text(text)
            )
            safe_text = html.escape(display_text).replace("\n", "<br>")
            if op == 0:
                fragments.append(safe_text)
            elif op < 0:
                fragments.append(
                    '<span style="background:#fce8e6;color:#b3261e;'
                    f'text-decoration:line-through;">{safe_text}</span>'
                )
            else:
                fragments.append(
                    '<span style="background:#d2e3fc;color:#174ea6;">'
                    f"{safe_text}</span>"
                )

        return (
            "<div style='font-family: Segoe UI, Arial, sans-serif; "
            "font-size: 14px; line-height: 1.7;'>"
            + "".join(fragments)
            + "</div>"
        )

    @staticmethod
    def _mask_answer_text(text: str) -> str:
        return "".join(char if char.isspace() else "*" for char in text)
