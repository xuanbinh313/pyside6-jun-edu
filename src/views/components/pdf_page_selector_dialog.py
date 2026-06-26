from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QPointF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
        initial_part: int = 1,
        selected_pages_by_part: dict[int, list[int]] | None = None,
        lane_label: str = "pages",
    ):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.initial_part = initial_part
        self.selected_pages_by_part: dict[int, list[int]] = {
            int(part): sorted(set(pages))
            for part, pages in (selected_pages_by_part or {}).items()
            if pages
        }
        if selected_pages and initial_part not in self.selected_pages_by_part:
            self.selected_pages_by_part[initial_part] = sorted(set(selected_pages))
        self.selected_pages: list[int] = list(
            self.selected_pages_by_part.get(initial_part, [])
        )
        self._pdf_buffer: QBuffer | None = None
        self._thumbnail_row = 0
        self._thumbnail_document = None
        self._updating_part_selection = False
        self._syncing_preview_selection = False
        self._build_ui(action_text, lane_label)
        self._load_pdf()

    def _build_ui(self, action_text: str, lane_label: str) -> None:
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

        part_row = QHBoxLayout()
        part_row.addWidget(QLabel("Save to", left_panel))
        self.part_combo = QComboBox(left_panel)
        for part in range(1, 8):
            self.part_combo.addItem(f"Part {part}", part)
        initial_index = max(0, self.initial_part - 1)
        self.part_combo.setCurrentIndex(initial_index)
        self.add_selected_btn = QPushButton("Add Selected", left_panel)
        self.add_selected_btn.setToolTip(
            f"Save checked {lane_label} to the selected TOEIC part"
        )
        part_row.addWidget(self.part_combo, 1)
        part_row.addWidget(self.add_selected_btn)
        left_layout.addLayout(part_row)

        self.page_list = QListWidget(left_panel)
        self.page_list.setIconSize(QSize(64, 90))
        self.page_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.page_list.setMinimumWidth(220)
        self.page_list.setStyleSheet(
            "QListWidget { border: 1px solid #dadce0; border-radius: 4px; }"
            "QListWidget::item { padding: 6px; }"
        )
        left_layout.addWidget(self.page_list, 1)
        splitter.addWidget(left_panel)

        self.preview = QPdfView(splitter)
        self.preview.setPageMode(QPdfView.PageMode.MultiPage)
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
        self.part_combo.currentIndexChanged.connect(self._on_part_changed)
        self.add_selected_btn.clicked.connect(self._add_selected_to_part)
        self.page_list.currentRowChanged.connect(self._preview_page)
        self.page_list.itemChanged.connect(self._on_item_changed)
        self.preview.pageNavigator().currentPageChanged.connect(
            self._select_thumbnail_for_page
        )
        self.cancel_btn.clicked.connect(self.reject)
        self.send_btn.clicked.connect(self._accept_if_selected)

        self.thumbnail_timer = QTimer(self)
        self.thumbnail_timer.setInterval(80)
        self.thumbnail_timer.timeout.connect(self._render_next_thumbnail)

    def _load_pdf(self) -> None:
        pdf_bytes = QByteArray(Path(self.pdf_path).read_bytes())
        self._pdf_buffer = QBuffer(self)
        self._pdf_buffer.setData(pdf_bytes)
        self._pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.document.load(self._pdf_buffer)
        if self.document.status() == QPdfDocument.Status.Error:
            QMessageBox.critical(self, "PDF Error", "Could not load the selected PDF.")
            self.send_btn.setEnabled(False)
            return

        try:
            import fitz
        except ImportError:
            self._thumbnail_document = None
        else:
            self._thumbnail_document = fitz.open(self.pdf_path)

        page_count = self.document.pageCount()
        self.page_list.blockSignals(True)
        self.page_list.clear()
        for page_index in range(page_count):
            item = QListWidgetItem(f"Page {page_index + 1}")
            item.setData(Qt.ItemDataRole.UserRole, page_index)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if page_index in self._current_part_pages()
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
        pixmap = self._render_thumbnail_pixmap(page_index, QSize(64, 90))
        if not pixmap.isNull():
            item.setIcon(QIcon(pixmap))
        self._thumbnail_row += 1

    def _render_thumbnail_pixmap(self, page_index: int, target_size: QSize) -> QPixmap:
        if self._thumbnail_document is None:
            return QPixmap()

        try:
            page = self._thumbnail_document[page_index]
            rect = page.rect
            scale = min(
                target_size.width() / max(rect.width, 1),
                target_size.height() / max(rect.height, 1),
            )
            pix = page.get_pixmap(matrix=self._fitz_matrix(scale), alpha=False)
            thumbnail = QPixmap()
            thumbnail.loadFromData(pix.tobytes("png"), "PNG")
            return thumbnail
        except Exception:
            return QPixmap()

    def _fitz_matrix(self, scale: float):
        import fitz

        return fitz.Matrix(scale, scale)

    def _preview_page(self, row: int) -> None:
        if row < 0 or self._syncing_preview_selection:
            return
        navigator = self.preview.pageNavigator()
        navigator.jump(row, QPointF(0, 0))

    def _select_thumbnail_for_page(self, page_index: int) -> None:
        if page_index < 0 or page_index >= self.page_list.count():
            return

        self._syncing_preview_selection = True
        try:
            self.page_list.setCurrentRow(page_index)
            item = self.page_list.item(page_index)
            if item is not None:
                self.page_list.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
        finally:
            self._syncing_preview_selection = False

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating_part_selection:
            return
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

    def _on_part_changed(self) -> None:
        self.selected_pages = self._current_part_pages()
        self._apply_checked_pages(self.selected_pages)
        self._refresh_status()

    def _add_selected_to_part(self) -> None:
        if not self.selected_pages:
            QMessageBox.warning(self, "No Pages", "Select at least one page.")
            return

        part = self._current_part()
        self.selected_pages_by_part[part] = sorted(set(self.selected_pages))
        self._refresh_status()

    def _current_part(self) -> int:
        return int(self.part_combo.currentData() or self.initial_part)

    def _current_part_pages(self) -> list[int]:
        return list(self.selected_pages_by_part.get(self._current_part(), []))

    def _apply_checked_pages(self, page_indices: list[int]) -> None:
        checked_pages = set(page_indices)
        self._updating_part_selection = True
        self.page_list.blockSignals(True)
        try:
            for row in range(self.page_list.count()):
                item = self.page_list.item(row)
                page_index = int(item.data(Qt.ItemDataRole.UserRole))
                item.setCheckState(
                    Qt.CheckState.Checked
                    if page_index in checked_pages
                    else Qt.CheckState.Unchecked
                )
        finally:
            self.page_list.blockSignals(False)
            self._updating_part_selection = False

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
        current_part = self._current_part()
        self.add_selected_btn.setEnabled(count > 0)
        self.send_btn.setEnabled(
            count > 0 or any(self.selected_pages_by_part.values())
        )
        if not count:
            saved_parts = self._saved_parts_text()
            suffix = f" Saved: {saved_parts}" if saved_parts else ""
            self.status_label.setText(
                f"No pages selected for Part {current_part}.{suffix}"
            )
            return
        page_text = ", ".join(str(index + 1) for index in self.selected_pages)
        saved_parts = self._saved_parts_text()
        suffix = f" Saved: {saved_parts}" if saved_parts else ""
        self.status_label.setText(
            f"Part {current_part}: {count} page(s) selected: {page_text}.{suffix}"
        )

    def _saved_parts_text(self) -> str:
        parts = []
        for part, pages in sorted(self.selected_pages_by_part.items()):
            if not pages:
                continue
            page_text = ", ".join(str(index + 1) for index in pages)
            parts.append(f"Part {part} ({page_text})")
        return "; ".join(parts)

    def _accept_if_selected(self) -> None:
        if self.selected_pages:
            self.selected_pages_by_part[self._current_part()] = sorted(
                set(self.selected_pages)
            )
        if not any(self.selected_pages_by_part.values()):
            QMessageBox.warning(self, "No Pages", "Select at least one page.")
            return
        self.selected_pages = self.selected_pages_by_part.get(
            self.initial_part, self.selected_pages
        )
        self.accept()

    def closeEvent(self, event) -> None:
        self.thumbnail_timer.stop()
        self._close_documents()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self.thumbnail_timer.stop()
        self._close_documents()
        super().done(result)

    def _close_documents(self) -> None:
        if self._thumbnail_document is not None:
            self._thumbnail_document.close()
            self._thumbnail_document = None
        self.preview.setDocument(None)
        close_document = getattr(self.document, "close", None)
        if callable(close_document):
            close_document()
        if self._pdf_buffer is not None:
            self._pdf_buffer.close()
            self._pdf_buffer = None
