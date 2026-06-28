import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ICON_BUTTON_STYLE = """
    QPushButton { border: none; background-color: transparent; }
    QPushButton:hover { background-color: #e8f0fe; border-radius: 12px; }
"""


def context_audio_meta(ctx) -> dict:
    if not ctx:
        return {}
    return ctx.additional_meta if isinstance(ctx.additional_meta, dict) else {}


def context_audio_range(ctx) -> tuple[float, float]:
    meta = context_audio_meta(ctx)
    try:
        audio_start = float(meta.get("audio_start", 0.0) or 0.0)
    except (TypeError, ValueError):
        audio_start = 0.0
    try:
        audio_end = float(meta.get("audio_end", 0.0) or 0.0)
    except (TypeError, ValueError):
        audio_end = 0.0
    return audio_start, audio_end


def context_audio_icon_color(ctx) -> str:
    _, audio_end = context_audio_range(ctx)
    return "#1a73e8" if audio_end > 0.0 else "#5f6368"


def context_audio_tooltip(ctx) -> str:
    audio_start, audio_end = context_audio_range(ctx)
    if audio_end > 0.0:
        return f"Audio segment: {audio_start:.2f}s - {audio_end:.2f}s"
    return "Select audio segment from transcript"


def refresh_context_play_button(button: QPushButton, ctx) -> None:
    audio_start, audio_end = context_audio_range(ctx)
    has_audio = audio_end > 0.0
    button.setIcon(qta.icon("fa5s.play", color="#34a853" if has_audio else "#9aa0a6"))
    button.setEnabled(has_audio)
    if has_audio:
        button.setToolTip(f"Play segment: {audio_start:.2f}s - {audio_end:.2f}s")
    else:
        button.setToolTip("No audio segment selected")


class ExamContextSection(QWidget):
    def __init__(
        self,
        ctx,
        title_text: str,
        content_html: str,
        on_play,
        on_select_audio,
        on_edit,
        on_anchor,
        parent=None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(6)
        layout.addLayout(
            self._build_header(title_text, on_play, on_select_audio, on_edit)
        )
        layout.addWidget(self._build_body(content_html, on_anchor))

        self.note_label = QLabel()
        self.note_label.setTextFormat(Qt.TextFormat.RichText)
        self.note_label.setWordWrap(True)
        self.note_label.setVisible(False)
        self.note_label.setStyleSheet("""
            QLabel {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #f8f9fa;
                padding: 8px 10px;
                font-size: 12px;
                color: #3c4043;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.note_label)

    def _build_header(self, title_text, on_play, on_select_audio, on_edit):
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(title_text)
        title.setWordWrap(True)
        title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #1a73e8; padding: 0 2px;"
        )
        header_layout.addWidget(title, 1)

        play_btn = QPushButton()
        refresh_context_play_button(play_btn, self.ctx)
        play_btn.setFixedSize(24, 24)
        play_btn.setStyleSheet(ICON_BUTTON_STYLE)
        play_btn.clicked.connect(lambda checked=False: on_play(self.ctx))
        header_layout.addWidget(play_btn)

        audio_btn = QPushButton()
        audio_btn.setIcon(
            qta.icon("fa5s.music", color=context_audio_icon_color(self.ctx))
        )
        audio_btn.setToolTip(context_audio_tooltip(self.ctx))
        audio_btn.setFixedSize(24, 24)
        audio_btn.setStyleSheet(ICON_BUTTON_STYLE)
        audio_btn.clicked.connect(lambda checked=False: on_select_audio(self.ctx))
        header_layout.addWidget(audio_btn)

        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        edit_btn.setToolTip("Edit context")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet(ICON_BUTTON_STYLE)
        edit_btn.clicked.connect(lambda checked=False: on_edit(self.ctx))
        header_layout.addWidget(edit_btn)
        return header_layout

    def _build_body(self, content_html, on_anchor):
        body = QLabel(content_html)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setOpenExternalLinks(False)
        body.setWordWrap(True)
        body.linkActivated.connect(on_anchor)
        body.setStyleSheet("""
            QLabel {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #fffde7;
                padding: 10px;
                font-size: 13px;
                color: #202124;
                line-height: 1.6;
            }
        """)
        return body
