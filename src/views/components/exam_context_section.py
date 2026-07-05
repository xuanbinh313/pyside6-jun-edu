from typing import Any, Callable, Optional, Union, cast

import qtawesome as qta
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from src.models.exam import ExamContext

ICON_BUTTON_STYLE = """
    QPushButton { border: none; background-color: transparent; }
    QPushButton:hover { background-color: #e8f0fe; border-radius: 12px; }
"""


ContextCallback = Callable[[ExamContext], None]
ContextTagCallback = Callable[[ExamContext, QPushButton], None]
AnchorCallback = Callable[[Union[QUrl, str]], None]


def context_audio_meta(ctx: Optional[ExamContext]) -> dict[str, object]:
    if not ctx:
        return {}
    meta = cast(Any, ctx.additional_meta or {})
    if isinstance(meta, dict):
        return cast(dict[str, object], meta)
    if hasattr(meta, "model_dump"):
        dumped = meta.model_dump()
        return cast(dict[str, object], dumped) if isinstance(dumped, dict) else {}
    return {
        "audio_start": getattr(meta, "audio_start", 0.0),
        "audio_end": getattr(meta, "audio_end", 0.0),
        "note": getattr(meta, "note", ""),
    }


def _coerce_float(value: object) -> float:
    try:
        return float(cast(Union[str, bytes, int, float], value) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def context_audio_range(ctx: Optional[ExamContext]) -> tuple[float, float]:
    meta = context_audio_meta(ctx)
    return _coerce_float(meta.get("audio_start", 0.0)), _coerce_float(
        meta.get("audio_end", 0.0)
    )


def context_audio_icon_color(ctx: Optional[ExamContext]) -> str:
    _, audio_end = context_audio_range(ctx)
    return "#1a73e8" if audio_end > 0.0 else "#5f6368"


def context_audio_tooltip(ctx: Optional[ExamContext]) -> str:
    audio_start, audio_end = context_audio_range(ctx)
    if audio_end > 0.0:
        return f"Audio segment: {audio_start:.2f}s - {audio_end:.2f}s"
    return "Select audio segment from transcript"


def refresh_context_play_button(button: QPushButton, ctx: Optional[ExamContext]) -> None:
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
        ctx: ExamContext,
        title_text: str,
        content_html: str,
        on_play: ContextCallback,
        on_select_audio: ContextCallback,
        on_edit: ContextCallback,
        on_tags: ContextTagCallback,
        tag_names: list[str],
        on_anchor: AnchorCallback,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(6)
        layout.addLayout(
            self._build_header(
                title_text, on_play, on_select_audio, on_edit, on_tags, tag_names
            )
        )
        layout.addWidget(self._build_body(content_html, on_anchor))

        self.note_label = QLabel()
        self.note_label.setTextFormat(Qt.TextFormat.RichText)
        self.note_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
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

    def _build_header(
        self,
        title_text: str,
        on_play: ContextCallback,
        on_select_audio: ContextCallback,
        on_edit: ContextCallback,
        on_tags: ContextTagCallback,
        tag_names: list[str],
    ) -> QHBoxLayout:
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title_text)
        self.title_label.setWordWrap(True)
        self.title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.title_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #1a73e8; padding: 0 2px;"
        )
        header_layout.addWidget(self.title_label, 1)

        self.play_btn = QPushButton()
        refresh_context_play_button(self.play_btn, self.ctx)
        self.play_btn.setFixedSize(24, 24)
        self.play_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.play_btn.clicked.connect(lambda checked=False: on_play(self.ctx))
        header_layout.addWidget(self.play_btn)

        self.tag_btn = QPushButton()
        has_tags = bool(tag_names)
        self.tag_btn.setIcon(
            qta.icon("fa5s.tags", color="#1a73e8" if has_tags else "#5f6368")
        )
        self.tag_btn.setToolTip(
            "Tagged: " + ", ".join(tag_names)
            if has_tags
            else "Manage tags for this context"
        )
        self.tag_btn.setFixedSize(24, 24)
        self.tag_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.tag_btn.clicked.connect(
            lambda checked=False: on_tags(self.ctx, self.tag_btn)
        )
        header_layout.addWidget(self.tag_btn)

        self.audio_btn = QPushButton()
        self.audio_btn.setIcon(
            qta.icon("fa5s.music", color=context_audio_icon_color(self.ctx))
        )
        self.audio_btn.setToolTip(context_audio_tooltip(self.ctx))
        self.audio_btn.setFixedSize(24, 24)
        self.audio_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.audio_btn.clicked.connect(lambda checked=False: on_select_audio(self.ctx))
        header_layout.addWidget(self.audio_btn)

        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        edit_btn.setToolTip("Edit context")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet(ICON_BUTTON_STYLE)
        edit_btn.clicked.connect(lambda checked=False: on_edit(self.ctx))
        header_layout.addWidget(edit_btn)
        return header_layout

    def _build_body(self, content_html: str, on_anchor: AnchorCallback) -> QLabel:
        self.body_label = QLabel(content_html)
        self.body_label.setTextFormat(Qt.TextFormat.RichText)
        self.body_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.body_label.setOpenExternalLinks(False)
        self.body_label.setWordWrap(True)
        self.body_label.linkActivated.connect(on_anchor)
        self.body_label.setStyleSheet("""
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
        return self.body_label

    def update_context(
        self,
        ctx: ExamContext,
        title_text: str,
        content_html: str,
        tag_names: list[str],
    ) -> None:
        self.ctx = ctx
        self.title_label.setText(title_text)
        self.body_label.setText(content_html)
        refresh_context_play_button(self.play_btn, self.ctx)
        self.audio_btn.setIcon(
            qta.icon("fa5s.music", color=context_audio_icon_color(self.ctx))
        )
        self.audio_btn.setToolTip(context_audio_tooltip(self.ctx))
        has_tags = bool(tag_names)
        self.tag_btn.setIcon(
            qta.icon("fa5s.tags", color="#1a73e8" if has_tags else "#5f6368")
        )
        self.tag_btn.setToolTip(
            "Tagged: " + ", ".join(tag_names)
            if has_tags
            else "Manage tags for this context"
        )

    def update_tags(self, tag_names: list[str]) -> None:
        has_tags = bool(tag_names)
        self.tag_btn.setIcon(
            qta.icon("fa5s.tags", color="#1a73e8" if has_tags else "#5f6368")
        )
        self.tag_btn.setToolTip(
            "Tagged: " + ", ".join(tag_names)
            if has_tags
            else "Manage tags for this context"
        )
