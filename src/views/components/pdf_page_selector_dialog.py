from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class PdfPageSelectorDialog(QDialog):
    def __init__(
        self,
        pdf_path: str,
        selected_pages: list[int] | None = None,
        parent=None,
        action_text: str = "Send to agent",
    ):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.selected_pages: list[int] = sorted(set(selected_pages or []))
        self._thumbnail_row = 0
        self._build_ui(action_text)
        self._load_pdf()

    def _build_ui(self, action_text: str) -> None:
        self.setWindowTitle(f"Select PDF Pages - {Path(self.pdf_path).name}")
        self.resize(980, 720)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        header = QLabel(Path(self.pdf_path).name, self)
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #202124;")
        main_layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter, 1)

        left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        actions_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All", left_panel)
        self.clear_all_btn = QPushButton("Clear", left_panel)
        actions_row.addWidget(self.select_all_btn)
        actions_row.addWidget(self.clear_all_btn)
        left_layout.addLayout(actions_row)

        self.page_list = QListWidget(left_panel)
        self.page_list.setIconSize(QSize(92, 128))
        self.page_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.page_list.setMinimumWidth(220)
        self.page_list.setStyleSheet(
            "QListWidget { border: 1px solid #dadce0; border-radius: 4px; }"
            "QListWidget::item { padding: 6px; }"
        )
        left_layout.addWidget(self.page_list, 1)
        splitter.addWidget(left_panel)

        self.preview = QPdfView(splitter)
        self.preview.setPageMode(QPdfView.PageMode.SinglePage)
        self.preview.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        splitter.addWidget(self.preview)
        splitter.setSizes([260, 720])

        self.status_label = QLabel("No pages selected", self)
        self.status_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        self.button_box = QDialogButtonBox(self)
        self.cancel_btn = self.button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.send_btn = self.button_box.addButton(
            action_text, QDialogButtonBox.ButtonRole.AcceptRole
        )
        main_layout.addWidget(self.button_box)

        self.document = QPdfDocument(self)
        self.preview.setDocument(self.document)

        self.select_all_btn.clicked.connect(self._select_all)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.page_list.currentRowChanged.connect(self._preview_page)
        self.page_list.itemChanged.connect(self._on_item_changed)
        self.cancel_btn.clicked.connect(self.reject)
        self.send_btn.clicked.connect(self._accept_if_selected)

        self.thumbnail_timer = QTimer(self)
        self.thumbnail_timer.setInterval(8)
        self.thumbnail_timer.timeout.connect(self._render_next_thumbnail)

    def _load_pdf(self) -> None:
        status = self.document.load(self.pdf_path)
        if status != QPdfDocument.Error.None_:
            QMessageBox.critical(self, "PDF Error", "Could not load the selected PDF.")
            self.send_btn.setEnabled(False)
            return

        page_count = self.document.pageCount()
        self.page_list.blockSignals(True)
        self.page_list.clear()
        for page_index in range(page_count):
            item = QListWidgetItem(f"Page {page_index + 1}")
            item.setData(Qt.ItemDataRole.UserRole, page_index)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if page_index in self.selected_pages
                else Qt.CheckState.Unchecked
            )
            self.page_list.addItem(item)
        self.page_list.blockSignals(False)

        if page_count:
            self.page_list.setCurrentRow(0)
        self._refresh_status()
        self._thumbnail_row = 0
        self.thumbnail_timer.start()

    def _render_next_thumbnail(self) -> None:
        if self._thumbnail_row >= self.page_list.count():
            self.thumbnail_timer.stop()
            return

        item = self.page_list.item(self._thumbnail_row)
        page_index = int(item.data(Qt.ItemDataRole.UserRole))
        image = self.document.render(page_index, QSize(92, 128))
        if not image.isNull():
            item.setIcon(QIcon(QPixmap.fromImage(image)))
        self._thumbnail_row += 1

    def _preview_page(self, row: int) -> None:
        if row < 0:
            return
        navigator = self.preview.pageNavigator()
        navigator.jump(row, QPointF(0, 0))

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        page_index = int(item.data(Qt.ItemDataRole.UserRole))
        if item.checkState() == Qt.CheckState.Checked:
            if page_index not in self.selected_pages:
                self.selected_pages.append(page_index)
        else:
            self.selected_pages = [
                index for index in self.selected_pages if index != page_index
            ]
        self.selected_pages.sort()
        self._refresh_status()

    def _select_all(self) -> None:
        self.page_list.blockSignals(True)
        self.selected_pages = []
        for row in range(self.page_list.count()):
            item = self.page_list.item(row)
            item.setCheckState(Qt.CheckState.Checked)
            self.selected_pages.append(int(item.data(Qt.ItemDataRole.UserRole)))
        self.page_list.blockSignals(False)
        self._refresh_status()

    def _clear_all(self) -> None:
        self.page_list.blockSignals(True)
        for row in range(self.page_list.count()):
            self.page_list.item(row).setCheckState(Qt.CheckState.Unchecked)
        self.page_list.blockSignals(False)
        self.selected_pages = []
        self._refresh_status()

    def _refresh_status(self) -> None:
        count = len(self.selected_pages)
        self.send_btn.setEnabled(count > 0)
        if not count:
            self.status_label.setText("No pages selected")
            return
        page_text = ", ".join(str(index + 1) for index in self.selected_pages)
        self.status_label.setText(f"{count} page(s) selected: {page_text}")

    def _accept_if_selected(self) -> None:
        if not self.selected_pages:
            QMessageBox.warning(self, "No Pages", "Select at least one page.")
            return
        self.accept()

    def closeEvent(self, event) -> None:
        self.thumbnail_timer.stop()
        super().closeEvent(event)
