from __future__ import annotations

from collections.abc import Callable

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)
from src.models.exam import Vocabulary
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
        self._is_populating = False

        header = self.ui.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.table.verticalHeader().setVisible(False)

        self.ui.back_button.clicked.connect(self._navigate_back)
        self.ui.search_input.textChanged.connect(self.viewmodel.set_search_query)
        self.ui.table.itemChanged.connect(self._on_item_changed)
        self.viewmodel.data_changed.connect(self._populate)
        self.viewmodel.error_occurred.connect(self._show_error)
        self.viewmodel.load_vocabulary()

    def _populate(self) -> None:
        self._is_populating = True
        self.ui.table.blockSignals(True)
        try:
            self.ui.table.setRowCount(len(self.viewmodel.vocabulary))
            for row, vocabulary in enumerate(self.viewmodel.vocabulary):
                self._populate_row(row, vocabulary)
            self.ui.table.resizeRowsToContents()
        finally:
            self.ui.table.blockSignals(False)
            self._is_populating = False

    def _populate_row(self, row: int, vocabulary: Vocabulary) -> None:
        word_item = QTableWidgetItem(vocabulary.word)
        word_item.setFlags(word_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        word_item.setData(Qt.ItemDataRole.UserRole, vocabulary.id)
        self.ui.table.setItem(row, 0, word_item)

        meaning_item = QTableWidgetItem(vocabulary.meaning or "")
        meaning_item.setToolTip("Double-click to edit the meaning")
        self.ui.table.setItem(row, 1, meaning_item)

        source_item = QTableWidgetItem(vocabulary.source_text or "")
        source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        source_item.setToolTip(vocabulary.source_text or "")
        self.ui.table.setItem(row, 2, source_item)
        self.ui.table.setCellWidget(row, 3, self._status_widget(vocabulary))
        self.ui.table.setCellWidget(row, 4, self._delete_widget(vocabulary))

    def _status_widget(self, vocabulary: Vocabulary) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        for status in range(1, 6):
            label = "✓" if status == 5 else str(status)
            button = QPushButton(label)
            button.setFixedSize(30, 28)
            button.setToolTip("Known" if status == 5 else f"Status {status}")
            color = self.STATUS_COLORS[status]
            if vocabulary.status == status:
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

    def _delete_widget(self, vocabulary: Vocabulary) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        button = QPushButton()
        button.setIcon(qta.icon("fa5s.trash-alt", color="#d93025"))
        button.setToolTip(f'Delete "{vocabulary.word}"')
        button.clicked.connect(
            lambda _checked=False, item=vocabulary: self._confirm_delete(item)
        )
        layout.addWidget(button)
        return container

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_populating or item.column() != 1:
            return
        id_item = self.ui.table.item(item.row(), 0)
        if id_item is None:
            return
        vocab_id = id_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(vocab_id, str):
            self.viewmodel.update_meaning(vocab_id, item.text())

    def _confirm_delete(self, vocabulary: Vocabulary) -> None:
        answer = QMessageBox.question(
            self,
            "Delete Vocabulary",
            f'Delete "{vocabulary.word}" from your vocabulary?',
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.viewmodel.delete_vocabulary(vocabulary.id)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Vocabulary Error", message)
