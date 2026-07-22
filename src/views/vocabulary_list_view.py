from __future__ import annotations

from collections.abc import Callable

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from src.models.exam import Vocabulary
from src.utils.qt import clear_layout
from src.viewmodels.vocabulary_list_viewmodel import VocabularyListViewModel
from ui_gen.ui_vocabulary_list_view import Ui_VocabularyListView


class VocabularyListView(QWidget):
    STATUS_COLORS = {
        1: "#ef6c00",
        2: "#fb8c00",
        3: "#fdd835",
        4: "#9ccc65",
        5: "#2e7d32",
    }

    def __init__(
        self,
        viewmodel: VocabularyListViewModel,
        navigate_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_VocabularyListView()
        self.ui.setupUi(self)
        self.viewmodel = viewmodel
        self._navigate_back = navigate_back
        self._progress_dialog: QProgressDialog | None = None

        self.ui.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.ui.cards_layout.setContentsMargins(4, 8, 4, 8)
        self.ui.cards_layout.setSpacing(10)
        self.ui.translate_button.setIcon(qta.icon("fa5s.robot", color="#ffffff"))
        self.ui.translate_button.setStyleSheet(
            "QPushButton { background: #1a73e8; color: white; border: none; "
            "border-radius: 4px; padding: 7px 12px; font-weight: 600; }"
            "QPushButton:disabled { background: #9aa0a6; }"
        )

        self.ui.back_button.clicked.connect(self._navigate_back)
        self.ui.search_input.textChanged.connect(self.viewmodel.set_search_query)
        self.ui.due_only_checkbox.toggled.connect(self.viewmodel.set_due_only)
        self.ui.translate_button.clicked.connect(self.viewmodel.translate_empty_meanings)
        self.viewmodel.data_changed.connect(self._populate)
        self.viewmodel.error_occurred.connect(self._show_error)
        self.viewmodel.translation_started.connect(self._on_translation_started)
        self.viewmodel.translation_progress.connect(self._on_translation_progress)
        self.viewmodel.translation_finished.connect(self._on_translation_finished)
        self.viewmodel.load_vocabulary()

    def _populate(self) -> None:
        clear_layout(self.ui.cards_layout)
        if not self.viewmodel.vocabulary:
            empty_label = QLabel("No vocabulary found.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #5f6368; padding: 36px;")
            self.ui.cards_layout.addWidget(empty_label)
            self.ui.cards_layout.addStretch(1)
            return

        for vocabulary in self.viewmodel.vocabulary:
            self.ui.cards_layout.addWidget(self._card_widget(vocabulary))
        self.ui.cards_layout.addStretch(1)

    def _card_widget(self, vocabulary: Vocabulary) -> QFrame:
        card = QFrame()
        card.setObjectName("vocabularyCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        card.setStyleSheet(
            "QFrame#vocabularyCard { background: #ffffff; border: 1px solid #dadce0; "
            "border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        word_label = QLabel(vocabulary.word)
        word_label.setWordWrap(True)
        word_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        word_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #202124;")
        header_layout.addWidget(word_label, 1)
        header_layout.addWidget(self._delete_button(vocabulary), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_layout)

        layout.addWidget(self._meaning_widget(vocabulary))

        source_text = (vocabulary.source_text or "").strip()
        if source_text:
            source_label = QLabel(source_text)
            source_label.setWordWrap(True)
            source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            source_label.setStyleSheet(
                "color: #5f6368; background: #f8fafd; border-radius: 6px; "
                "padding: 8px;"
            )
            layout.addWidget(source_label)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addWidget(self._status_widget(vocabulary), 0)
        footer_layout.addStretch(1)
        layout.addLayout(footer_layout)
        return card

    def _meaning_widget(self, vocabulary: Vocabulary) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        meaning_text = (vocabulary.meaning or "").strip()
        meaning_label = QLabel(meaning_text or "No meaning yet")
        meaning_label.setWordWrap(True)
        meaning_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        meaning_label.setStyleSheet(
            "color: #202124;" if meaning_text else "color: #9aa0a6; font-style: italic;"
        )
        meaning_edit = QLineEdit(meaning_text)
        meaning_edit.setVisible(False)
        meaning_edit.setPlaceholderText("Enter meaning...")

        edit_button = QPushButton()
        edit_button.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        edit_button.setToolTip("Edit meaning")
        edit_button.setFixedSize(34, 30)

        def start_edit() -> None:
            meaning_label.setVisible(False)
            meaning_edit.setVisible(True)
            meaning_edit.setFocus()
            meaning_edit.selectAll()
            edit_button.setIcon(qta.icon("fa5s.save", color="#188038"))
            edit_button.setToolTip("Save meaning")
            try:
                edit_button.clicked.disconnect()
            except RuntimeError:
                pass
            edit_button.clicked.connect(save_edit)

        def save_edit() -> None:
            self.viewmodel.update_meaning(vocabulary.id, meaning_edit.text())

        meaning_edit.returnPressed.connect(save_edit)
        edit_button.clicked.connect(start_edit)

        layout.addWidget(meaning_label, 1)
        layout.addWidget(meaning_edit, 1)
        layout.addWidget(edit_button, 0, Qt.AlignmentFlag.AlignTop)
        return container

    def _status_widget(self, vocabulary: Vocabulary) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for status in range(1, 6):
            button = QPushButton(str(status))
            button.setFixedSize(30, 28)
            button.setToolTip("Known" if status == 5 else f"Status {status}")
            color = self.STATUS_COLORS[status]
            if vocabulary.reps > 0 and vocabulary.status == status:
                text_color = "#ffffff" if status != 3 else "#202124"
                button.setStyleSheet(
                    f"background: {color}; color: {text_color}; "
                    "border: none; border-radius: 4px; font-weight: bold;"
                )
            else:
                button.setStyleSheet(
                    "background: #f1f3f4; color: #5f6368; "
                    "border: 1px solid #dadce0; border-radius: 4px;"
                )
            button.clicked.connect(
                lambda _checked=False, vocab_id=vocabulary.id, value=status:
                self.viewmodel.update_status(vocab_id, value)
            )
            layout.addWidget(button)
        return container

    def _delete_button(self, vocabulary: Vocabulary) -> QPushButton:
        button = QPushButton()
        button.setIcon(qta.icon("fa5s.trash-alt", color="#d93025"))
        button.setToolTip(f'Delete "{vocabulary.word}"')
        button.setFixedSize(34, 30)
        button.clicked.connect(
            lambda _checked=False, item=vocabulary: self._confirm_delete(item)
        )
        return button

    def _confirm_delete(self, vocabulary: Vocabulary) -> None:
        answer = QMessageBox.question(
            self,
            "Delete Vocabulary",
            f'Delete "{vocabulary.word}" from your vocabulary?',
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.viewmodel.delete_vocabulary(vocabulary.id)

    def _on_translation_started(self, count: int) -> None:
        self.ui.translate_button.setEnabled(False)
        self._progress_dialog = QProgressDialog(
            f"Translating {count} vocabulary item(s)...",
            "",
            0,
            0,
            self,
        )
        self._progress_dialog.setWindowTitle("AI Translate Empty")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.show()

    def _on_translation_progress(self, message: str) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.setLabelText(message)

    def _on_translation_finished(self, count: int) -> None:
        self.ui.translate_button.setEnabled(True)
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None
        if count == 0:
            QMessageBox.information(
                self,
                "AI Translate Empty",
                "All vocabulary entries already have meanings.",
            )
        else:
            QMessageBox.information(
                self,
                "AI Translate Empty",
                f"Updated {count} vocabulary meaning(s).",
            )

    def _show_error(self, message: str) -> None:
        self.ui.translate_button.setEnabled(True)
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None
        QMessageBox.critical(self, "Vocabulary Error", message)
