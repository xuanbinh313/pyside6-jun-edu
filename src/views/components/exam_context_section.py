from typing import Any, Callable, Optional, Union, cast

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
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
VocabularyCallback = Callable[[str, str], None]


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


class VocabularyTextBrowser(QTextBrowser):
    def __init__(
        self,
        on_add_vocabulary: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_add_vocabulary = on_add_vocabulary
        self._selected_text = ""
        self.setReadOnly(True)
        self.setOpenExternalLinks(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(
            self._update_document_height
        )
        self.selectionChanged.connect(self._position_add_button)

        self.add_vocabulary_button = QPushButton("Add Vocab", self.viewport())
        self.add_vocabulary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_vocabulary_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #1a73e8;
                border-radius: 5px;
                background-color: #1a73e8;
                color: white;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1557b0; }
        """)
        self.add_vocabulary_button.adjustSize()
        self.add_vocabulary_button.hide()
        self.add_vocabulary_button.clicked.connect(self._add_selected_vocabulary)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        height = int(self.document().documentLayout().documentSize().height()) + 22
        return QSize(hint.width(), max(height, 44))

    def _update_document_height(self) -> None:
        self.setFixedHeight(self.sizeHint().height())

    def _position_add_button(self) -> None:
        cursor = self.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", " ").strip()
        self._selected_text = " ".join(selected_text.split())
        if not self._selected_text:
            self.add_vocabulary_button.hide()
            return

        selection_start = QTextCursor(cursor)
        selection_start.setPosition(cursor.selectionStart())
        selection_rect = self.cursorRect(selection_start)
        button_size = self.add_vocabulary_button.sizeHint()
        x = min(
            max(0, selection_rect.center().x() - (button_size.width() // 2)),
            max(0, self.viewport().width() - button_size.width()),
        )
        y = max(0, selection_rect.top() - button_size.height() - 4)
        self.add_vocabulary_button.move(x, y)
        self.add_vocabulary_button.show()
        self.add_vocabulary_button.raise_()

    def _add_selected_vocabulary(self) -> None:
        if self._selected_text:
            self._on_add_vocabulary(self._selected_text)
        self.add_vocabulary_button.hide()


class NoteTextBrowser(QTextBrowser):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.document().documentLayout().documentSizeChanged.connect(
            self._update_document_height
        )

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        height = int(self.document().documentLayout().documentSize().height()) + 22
        return QSize(hint.width(), max(height, 44))

    def _update_document_height(self) -> None:
        self.setFixedHeight(self.sizeHint().height())


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
        on_add_vocabulary: VocabularyCallback,
        show_select_audio: bool = True,
        show_edit: bool = True,
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
                title_text,
                on_play,
                on_select_audio,
                on_edit,
                on_tags,
                tag_names,
                show_select_audio,
                show_edit,
            )
        )
        layout.addWidget(
            self._build_body(content_html, on_anchor, on_add_vocabulary)
        )

        self.note_label = NoteTextBrowser(self)
        self.note_label.setVisible(False)
        self.note_label.setStyleSheet("""
            QTextBrowser {
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
        show_select_audio: bool,
        show_edit: bool,
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

        self.play_btn = QPushButton(self)
        refresh_context_play_button(self.play_btn, self.ctx)
        self.play_btn.setFixedSize(24, 24)
        self.play_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.play_btn.clicked.connect(lambda checked=False: on_play(self.ctx))
        header_layout.addWidget(self.play_btn)

        self.tag_btn = QPushButton(self)
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

        self.audio_btn = QPushButton(self)
        self.audio_btn.setIcon(
            qta.icon("fa5s.music", color=context_audio_icon_color(self.ctx))
        )
        self.audio_btn.setToolTip(context_audio_tooltip(self.ctx))
        self.audio_btn.setFixedSize(24, 24)
        self.audio_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.audio_btn.clicked.connect(lambda checked=False: on_select_audio(self.ctx))
        if show_select_audio:
            header_layout.addWidget(self.audio_btn)
        else:
            self.audio_btn.hide()

        self.edit_btn = QPushButton(self)
        self.edit_btn.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        self.edit_btn.setToolTip("Edit context")
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.edit_btn.clicked.connect(lambda checked=False: on_edit(self.ctx))
        if show_edit:
            header_layout.addWidget(self.edit_btn)
        else:
            self.edit_btn.hide()
        return header_layout

    def _build_body(
        self,
        content_html: str,
        on_anchor: AnchorCallback,
        on_add_vocabulary: VocabularyCallback,
    ) -> VocabularyTextBrowser:
        self.body_label = VocabularyTextBrowser(
            lambda word: on_add_vocabulary(word, self.ctx.id)
        )
        self.body_label.setHtml(content_html)
        self.body_label.anchorClicked.connect(on_anchor)
        self.body_label.setStyleSheet("""
            QTextBrowser {
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
        self.body_label.setHtml(content_html)
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
