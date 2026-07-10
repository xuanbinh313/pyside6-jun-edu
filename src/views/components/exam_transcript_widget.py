# Import the icon management library.
from typing import Callable, Optional

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.models.exam import ExamContext, ExamSrtChunk, SrtChunkMapping
from src.utils.helpers import get_local_media_path
from src.viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from src.viewmodels.srt_mapping_agent_viewmodel import SrtMappingAgentViewModel
from ui_gen.ui_exam_transcript_widget import Ui_ExamTranscriptWidget


class SelectExamContextDialog(QDialog):
    def __init__(
        self, viewmodel: ExamDetailsViewModel, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.selected_context = None

        self.setWindowTitle("Select Exam Context")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        label = QLabel("Select the question context to receive this audio segment.")
        layout.addWidget(label)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self):
        contexts = self.viewmodel.list_contexts()
        for ctx in contexts:
            item = QListWidgetItem(self._context_label(ctx))
            item.setData(Qt.ItemDataRole.UserRole, ctx)
            self.list_widget.addItem(item)

    def _context_label(self, ctx: ExamContext):
        numbers = self.viewmodel.context_question_numbers(ctx.id)
        type_label = ctx.context_type.replace("_", " ").title()
        if len(numbers) == 1:
            prefix = f"Question {numbers[0]}"
        elif numbers:
            prefix = f"Questions {numbers[0]}-{numbers[-1]}"
        else:
            prefix = f"Context {ctx.index}"
        return f"{prefix} - Part {ctx.part} - {type_label}"

    def _on_accept(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a context.")
            return
        self.selected_context = item.data(Qt.ItemDataRole.UserRole)
        self.accept()


class SrtMappingPreviewDialog(QDialog):
    def __init__(
        self,
        results: list[tuple[str, float, float]],
        viewmodel: ExamDetailsViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.results = results
        self.viewmodel = viewmodel

        self.setWindowTitle("Preview Auto-detected Audio")
        self.resize(760, 480)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Context", "Questions", "Start (s)", "End (s)"]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        apply_button.setText("Apply All")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        contexts = {context.id: context for context in self.viewmodel.list_contexts()}
        self.table.setRowCount(len(self.results))
        for row, (context_id, start_time, end_time) in enumerate(self.results):
            context = contexts.get(context_id)
            questions = self.viewmodel.context_question_numbers(context_id)
            values = [
                self._context_label(context, context_id, questions),
                ", ".join(str(number) for number in questions),
                f"{start_time:.3f}",
                f"{end_time:.3f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)

    def _context_label(
        self,
        context: Optional[ExamContext],
        context_id: str,
        numbers: list[int],
    ) -> str:
        if context is None:
            return f"Context {context_id}"
        type_label = context.context_type.replace("_", " ").title()
        if len(numbers) == 1:
            prefix = f"Question {numbers[0]}"
        elif numbers:
            prefix = f"Questions {numbers[0]}-{numbers[-1]}"
        else:
            prefix = f"Context {context.index}"
        return f"{prefix} - Part {context.part} - {type_label}"


class TimeAdjustWidget(QWidget):
    def __init__(
        self,
        value: float,
        on_change: Callable[[float], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.on_change = on_change
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Add a muted red minus icon.
        self.minus_btn = QPushButton()
        self.minus_btn.setFixedWidth(22)
        self.minus_btn.setIcon(qta.icon("fa5s.minus", color="#c53929"))
        self.minus_btn.clicked.connect(self._minus)
        layout.addWidget(self.minus_btn)

        self.val_edit = QLineEdit(f"{value:.3f}")
        self.val_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_edit.editingFinished.connect(self._text_changed)
        layout.addWidget(self.val_edit)

        # Add a blue plus icon.
        self.plus_btn = QPushButton()
        self.plus_btn.setFixedWidth(22)
        self.plus_btn.setIcon(qta.icon("fa5s.plus", color="#1a73e8"))
        self.plus_btn.clicked.connect(self._plus)
        layout.addWidget(self.plus_btn)

    def _minus(self):
        val = max(0.0, float(self.val_edit.text()) - 0.1)
        self.val_edit.setText(f"{val:.3f}")
        self.on_change(val)

    def _plus(self):
        val = float(self.val_edit.text()) + 0.1
        self.val_edit.setText(f"{val:.3f}")
        self.on_change(val)

    def _text_changed(self):
        try:
            val = max(0.0, float(self.val_edit.text()))
            self.on_change(val)
        except ValueError:
            pass


class ExamTranscriptWidget(QWidget):
    def __init__(
        self, viewmodel: ExamDetailsViewModel, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self._srt_mapping_vm = SrtMappingAgentViewModel(self)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        # Watch media state changes to update the Play/Pause icon automatically.
        self.player.playbackStateChanged.connect(self._update_play_pause_icon)

        self.play_until = None
        self.looping_chunk_idx = None
        self._current_highlighted_row = None
        self._has_changes = False
        self._split_editor_chunk: Optional[ExamSrtChunk] = None
        self._split_editor_row: Optional[int] = None
        self._split_editor_text: str = ""
        self._split_cursor_position: int = 0

        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_ExamTranscriptWidget()
        self.ui.setupUi(self)

        # Configure the main Play/Pause button.
        self.ui.play_pause_btn.clicked.connect(self._toggle_play)
        self._update_play_pause_icon()  # Initialize the icon.

        self.ui.add_to_question_btn.setIcon(qta.icon("fa5s.plus", color="white"))
        self.ui.add_to_question_btn.setIconSize(QSize(16, 16))
        self.ui.add_to_question_btn.setStyleSheet(
            "QPushButton { background-color: #34a853; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #dadce0; color: #5f6368; }"
            "QPushButton:hover:!disabled { background-color: #188038; }"
        )
        self.ui.add_to_question_btn.clicked.connect(self._on_add_to_question_clicked)

        self.auto_detect_audio_btn = QPushButton("Auto-detect Audio", self)
        self.auto_detect_audio_btn.setIcon(qta.icon("fa5s.robot", color="white"))
        self.auto_detect_audio_btn.setIconSize(QSize(16, 16))
        self.auto_detect_audio_btn.setStyleSheet(
            "QPushButton { background-color: #673ab7; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #dadce0; color: #5f6368; }"
            "QPushButton:hover:!disabled { background-color: #512da8; }"
        )
        self.auto_detect_audio_btn.clicked.connect(self._on_auto_detect_audio_clicked)
        self.ui.audio_controls.insertWidget(4, self.auto_detect_audio_btn)

        self._srt_mapping_vm.mapping_ready.connect(self._on_mapping_ready)
        self._srt_mapping_vm.progress_message.connect(self._show_mapping_progress)
        self._srt_mapping_vm.error_message.connect(self._show_mapping_error)

        self.ui.save_btn.setIcon(qta.icon("fa5s.save", color="white"))
        self.ui.save_btn.setIconSize(QSize(16, 16))
        self.ui.save_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
        self.ui.save_btn.clicked.connect(self._on_save_clicked)
        self.ui.save_btn.setVisible(False)

        self.ui.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.ui.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.ui.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ui.table.itemChanged.connect(self._on_item_changed)
        self.ui.table.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        self.ui.table.itemSelectionChanged.connect(self._hide_split_float_button)
        self.ui.table.selectionModel().selectionChanged.connect(
            self._update_add_to_question_enabled
        )

        self.split_float_btn = QPushButton(self.ui.table.viewport())
        self.split_float_btn.setFixedSize(24, 24)
        self.split_float_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.split_float_btn.setIcon(qta.icon("fa5s.cut", color="#ffffff"))
        self.split_float_btn.setToolTip("Split at cursor")
        self.split_float_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; border-radius: 12px; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
        self.split_float_btn.clicked.connect(self._split_current_editor_text)
        self.split_float_btn.hide()

        # Seek bar
        self.ui.seek_slider.setTracking(False)  # only emit on release
        self.ui.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.ui.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.ui.seek_slider.sliderReleased.connect(self._on_slider_released)
        self._slider_dragging = False

        self.ui.seek_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #dadce0; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #1a73e8; border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -4px 0;"
            " background: #1a73e8; border-radius: 7px; }"
        )

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _update_play_pause_icon(self):
        """Update the Play/Pause button styling from Python."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.ui.play_pause_btn.setIcon(qta.icon("fa5s.pause", color="#d93025"))
            self.ui.play_pause_btn.setText(" Pause")
        else:
            self.ui.play_pause_btn.setIcon(qta.icon("fa5s.play", color="#1e8e3e"))
            self.ui.play_pause_btn.setText(" Play Audio")
        self.ui.play_pause_btn.setIconSize(QSize(16, 16))

    @staticmethod
    def _fmt_time(ms: int) -> str:
        # s = int(ms / 1000)
        # m, s = divmod(s, 60)
        return f"{ms / 1000.0:.3f}"

    def _on_duration_changed(self, duration_ms: int):
        self.ui.seek_slider.setMaximum(max(duration_ms, 1))
        self.ui.time_total_label.setText(self._fmt_time(duration_ms))

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_moved(self, value: int):
        self.ui.time_current_label.setText(self._fmt_time(value))

    def _on_slider_released(self):
        self._slider_dragging = False
        self.player.setPosition(self.ui.seek_slider.value())

    def _on_position_changed(self, pos_ms: int):
        if self.play_until and pos_ms >= self.play_until:
            self.player.pause()

            loop_idx = self.looping_chunk_idx
            self.play_until = None

            if loop_idx is not None:
                delay_ms = self.ui.delay_spin.value() * 1000
                QTimer.singleShot(delay_ms, lambda: self._play_loop(loop_idx))

        # Update seek slider & time label (skip if user is dragging)
        if not self._slider_dragging:
            self.ui.seek_slider.blockSignals(True)
            self.ui.seek_slider.setValue(pos_ms)
            self.ui.seek_slider.blockSignals(False)
            self.ui.time_current_label.setText(self._fmt_time(pos_ms))

        pos_sec = pos_ms / 1000.0
        for row, chunk in enumerate(self.viewmodel.srt_chunks):
            if chunk.start_time <= pos_sec <= chunk.end_time:
                if getattr(self, "_current_highlighted_row", None) != row:
                    self._set_playback_highlight(row)
                break

    def _set_playback_highlight(self, row: int):
        if self._current_highlighted_row is not None:
            self._set_row_background(self._current_highlighted_row, QBrush())
        self._set_row_background(row, QBrush(QColor("#e8f0fe")))
        self._current_highlighted_row = row

    def _set_row_background(self, row: int, brush: QBrush):
        for column in (0, 3):
            item = self.ui.table.item(row, column)
            if item:
                item.setBackground(brush)

    def _play_loop(self, loop_idx: int):
        if self.looping_chunk_idx != loop_idx:
            return

        chunk = next(
            (c for c in self.viewmodel.srt_chunks if c.index == loop_idx), None
        )
        if chunk:
            self.play_range(chunk.start_time, chunk.end_time, loop_idx)

    def play_range(
        self, start_time: float, end_time: float, loop_idx: Optional[int] = None
    ):
        self.looping_chunk_idx = loop_idx
        if loop_idx is not None:
            self.play_until = int(end_time * 1000)
        self.player.setPosition(int(start_time * 1000))
        self.player.play()

    def populate(self):
        self.ui.table.blockSignals(True)
        self.ui.table.setRowCount(0)
        self._has_changes = False
        self.ui.save_btn.setVisible(False)

        if self.viewmodel.exam and self.viewmodel.exam.audio_name:
            path = get_local_media_path(self.viewmodel.exam.audio_name)
            if path.exists():
                self.player.setSource(QUrl.fromLocalFile(str(path)))

        for row, chunk in enumerate(self.viewmodel.srt_chunks):
            self._insert_chunk_row(row, chunk)

        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()

    def _insert_chunk_row(self, row: int, chunk: ExamSrtChunk):
        self.ui.table.insertRow(row)

        idx_item = QTableWidgetItem(str(chunk.index))
        idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.ui.table.setItem(row, 0, idx_item)

        # Start Time
        start_w = TimeAdjustWidget(
            chunk.start_time, lambda v, c=chunk: self._update_time(c, "start", v)
        )
        self.ui.table.setCellWidget(row, 1, start_w)

        # End Time
        end_w = TimeAdjustWidget(
            chunk.end_time, lambda v, c=chunk: self._update_time(c, "end", v)
        )
        self.ui.table.setCellWidget(row, 2, end_w)

        # Text
        text_item = QTableWidgetItem(chunk.text)
        self.ui.table.setItem(row, 3, text_item)

        # --- Add icons for each row action button. ---
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        # 1. Preview button (Play Once) -> green
        play_btn = QPushButton()
        play_btn.setFixedSize(16, 16)
        play_btn.setIcon(qta.icon("fa5s.play", color="#1e8e3e"))
        play_btn.setToolTip("Play Once")

        def on_play_clicked(checked: bool = False, c: ExamSrtChunk = chunk) -> None:
            self.play_range(c.start_time, c.end_time)

        play_btn.clicked.connect(on_play_clicked)
        action_layout.addWidget(play_btn)

        # 2. Loop segment button -> blue
        loop_btn = QPushButton()
        loop_btn.setFixedSize(16, 16)
        loop_btn.setIcon(qta.icon("fa5s.sync-alt", color="#1a73e8"))
        loop_btn.setToolTip("Loop")

        def on_loop_clicked(checked: bool = False, c: ExamSrtChunk = chunk) -> None:
            self._toggle_loop(c)

        loop_btn.clicked.connect(on_loop_clicked)
        action_layout.addWidget(loop_btn)

        # 3. Duplicate button -> amber
        dup_btn = QPushButton()
        dup_btn.setFixedSize(16, 16)
        dup_btn.setIcon(qta.icon("fa5s.copy", color="#f9ab00"))
        dup_btn.setToolTip("Duplicate")

        def on_duplicate_clicked(
            checked: bool = False, c: ExamSrtChunk = chunk
        ) -> None:
            self._duplicate_chunk(c)

        dup_btn.clicked.connect(on_duplicate_clicked)
        action_layout.addWidget(dup_btn)

        # 4. Merge next row button -> dark gray
        merge_btn = QPushButton()
        merge_btn.setFixedSize(16, 16)
        merge_btn.setIcon(qta.icon("fa5s.compress-arrows-alt", color="#5f6368"))
        merge_btn.setToolTip("Merge Next")

        def on_merge_clicked(checked: bool = False, c: ExamSrtChunk = chunk) -> None:
            self._merge_chunk(c)

        merge_btn.clicked.connect(on_merge_clicked)
        action_layout.addWidget(merge_btn)

        # 5. Split text at the current editor cursor -> blue
        split_btn = QPushButton()
        split_btn.setFixedSize(16, 16)
        split_btn.setIcon(qta.icon("fa5s.cut", color="#1a73e8"))
        split_btn.setToolTip("Split")

        def on_split_clicked(checked: bool = False, c: ExamSrtChunk = chunk) -> None:
            self._start_split_edit(c)

        split_btn.clicked.connect(on_split_clicked)
        action_layout.addWidget(split_btn)

        # 6. Delete row -> red
        delete_btn = QPushButton()
        delete_btn.setFixedSize(16, 16)
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color="#d93025"))
        delete_btn.setToolTip("Delete")

        def on_delete_clicked(checked: bool = False, c: ExamSrtChunk = chunk) -> None:
            self._delete_chunk(c)

        delete_btn.clicked.connect(on_delete_clicked)
        action_layout.addWidget(delete_btn)

        self.ui.table.setCellWidget(row, 4, action_widget)

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self.ui.save_btn.setVisible(True)

    def _on_save_clicked(self):
        self.viewmodel.save_chunks()
        self._has_changes = False
        self.ui.save_btn.setVisible(False)

    def _refresh_row_indexes(self, start_row: int = 0) -> None:
        for row in range(start_row, self.ui.table.rowCount()):
            if row >= len(self.viewmodel.srt_chunks):
                break
            idx_item = self.ui.table.item(row, 0)
            if idx_item is not None:
                idx_item.setText(str(self.viewmodel.srt_chunks[row].index))

    def _update_chunk_row(self, row: int, chunk: ExamSrtChunk) -> None:
        idx_item = self.ui.table.item(row, 0)
        if idx_item is not None:
            idx_item.setText(str(chunk.index))

        start_widget = self.ui.table.cellWidget(row, 1)
        if isinstance(start_widget, TimeAdjustWidget):
            start_widget.val_edit.setText(f"{chunk.start_time:.3f}")

        end_widget = self.ui.table.cellWidget(row, 2)
        if isinstance(end_widget, TimeAdjustWidget):
            end_widget.val_edit.setText(f"{chunk.end_time:.3f}")

        text_item = self.ui.table.item(row, 3)
        if text_item is not None:
            text_item.setText(chunk.text)

    def _selected_chunks(self) -> list[ExamSrtChunk]:
        chunks: list[ExamSrtChunk] = []
        rows = sorted({index.row() for index in self.ui.table.selectedIndexes()})
        for row in rows:
            idx_item = self.ui.table.item(row, 0)
            if idx_item is None:
                continue
            idx = int(idx_item.text())

            chunk: Optional[ExamSrtChunk] = next(
                (c for c in self.viewmodel.srt_chunks if c.index == idx), None
            )
            if chunk:
                chunks.append(chunk)
        return chunks

    def _update_add_to_question_enabled(self):
        self.ui.add_to_question_btn.setEnabled(bool(self._selected_chunks()))

    def _on_add_to_question_clicked(self):
        selected_chunks = self._selected_chunks()
        if not selected_chunks:
            self._update_add_to_question_enabled()
            return

        if not getattr(self.viewmodel, "exam_id", None):
            QMessageBox.warning(self, "No Exam", "Could not determine the exam.")
            return

        dialog = SelectExamContextDialog(self.viewmodel, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_context:
            return

        first = selected_chunks[0]
        last = selected_chunks[-1]
        ctx = dialog.selected_context
        try:
            updated_ctx = self.viewmodel.update_context_audio_segment(
                ctx.id, first.start_time, last.end_time
            )
            if not updated_ctx:
                QMessageBox.warning(self, "Missing Context", "Context not found.")
                return
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error Saving",
                f"Could not save segment to context:\n{exc}",
            )
            return

        self.ui.table.clearSelection()
        self._update_add_to_question_enabled()

    def _on_auto_detect_audio_clicked(self) -> None:
        if not getattr(self.viewmodel, "exam_id", None):
            QMessageBox.warning(self, "No Exam", "Could not determine the exam.")
            return

        contexts = self.viewmodel.list_contexts()
        questions_by_context = {
            context.id: self.viewmodel.list_questions_for_context(context.id)
            for context in contexts
        }
        self.auto_detect_audio_btn.setEnabled(False)
        self._srt_mapping_vm.start_mapping(
            chunks=self.viewmodel.srt_chunks,
            contexts=contexts,
            questions_by_context=questions_by_context,
        )

    def _show_mapping_progress(self, message: str) -> None:
        self.ui.title_label.setText(f"Transcript Chunks - {message}")

    def _show_mapping_error(self, message: str) -> None:
        self.auto_detect_audio_btn.setEnabled(True)
        self.ui.title_label.setText("Transcript Chunks")
        QMessageBox.critical(self, "Auto-detect Audio Failed", message)

    def _on_mapping_ready(self, mappings: list[SrtChunkMapping]) -> None:
        self.auto_detect_audio_btn.setEnabled(True)
        self.ui.title_label.setText("Transcript Chunks")
        results = self._srt_mapping_vm.resolve_times(
            mappings, self.viewmodel.srt_chunks
        )
        if not results:
            QMessageBox.information(
                self,
                "No Audio Detected",
                "No matching audio segments were returned.",
            )
            return

        dialog = SrtMappingPreviewDialog(results, self.viewmodel, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        saved_count = 0
        try:
            for context_id, start_time, end_time in results:
                updated_context = self.viewmodel.update_context_audio_segment(
                    context_id, start_time, end_time
                )
                if updated_context is not None:
                    saved_count += 1
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error Saving",
                f"Could not save auto-detected segments:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Audio Segments Saved",
            f"Saved audio segments for {saved_count} context(s).",
        )

    def _update_time(self, chunk: ExamSrtChunk, field: str, value: float):
        if field == "start":
            chunk.start_time = value
        elif field == "end":
            chunk.end_time = value
        self._mark_changed()

    def _on_item_changed(self, item: QTableWidgetItem):
        if item.column() == 3:
            row = item.row()
            idx_item = self.ui.table.item(row, 0)
            if idx_item is None:
                return
            idx_str = idx_item.text()
            idx = int(idx_str)
            chunk = next((c for c in self.viewmodel.srt_chunks if c.index == idx), None)
            if chunk:
                chunk.text = item.text()
                self._mark_changed()

    def _on_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        if item.column() != 3:
            return
        chunk = self._chunk_for_row(item.row())
        if not chunk:
            return
        self._split_editor_chunk = chunk
        QTimer.singleShot(0, self._show_split_float_button)

    def _toggle_loop(self, chunk: ExamSrtChunk):
        if self.looping_chunk_idx == chunk.index:
            self.looping_chunk_idx = None
            self.play_until = None
        else:
            self.play_range(chunk.start_time, chunk.end_time, chunk.index)

    def _duplicate_chunk(self, chunk: ExamSrtChunk):
        new_idx, new_chunk = self.viewmodel.duplicate_chunk(chunk)

        self.ui.table.blockSignals(True)
        self._insert_chunk_row(new_idx, new_chunk)
        self._refresh_row_indexes(new_idx)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()

    def _delete_chunk(self, chunk: ExamSrtChunk) -> None:
        if len(self.viewmodel.srt_chunks) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "At least one row is required.")
            return
        response = QMessageBox.question(
            self,
            "Delete Row",
            "Delete this transcript row?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        row = self._row_for_chunk(chunk)
        if row is None:
            return
        self.viewmodel.delete_chunk(chunk)
        self._hide_split_float_button()
        self.ui.table.blockSignals(True)
        self.ui.table.removeRow(row)
        self._refresh_row_indexes(row)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()

    def _start_split_edit(self, chunk: ExamSrtChunk) -> None:
        row = self._row_for_chunk(chunk)
        if row is None:
            return
        item = self.ui.table.item(row, 3)
        if item is None:
            return
        self._split_editor_chunk = chunk
        self._split_editor_row = row
        self._split_editor_text = item.text()
        self._split_cursor_position = len(item.text())
        self.ui.table.setCurrentCell(row, 3)
        self.ui.table.editItem(item)
        QTimer.singleShot(0, self._show_split_float_button)

    def _show_split_float_button(self) -> None:
        row = self.ui.table.currentRow()
        if row < 0 or self.ui.table.currentColumn() != 3:
            self._hide_split_float_button()
            return
        item = self.ui.table.item(row, 3)
        if item is None:
            self._hide_split_float_button()
            return
        editor = self._active_text_editor()
        if editor is not None:
            self._capture_split_editor_state(editor)
            editor.textChanged.connect(
                lambda text: self._capture_split_editor_text(text)
            )
            editor.cursorPositionChanged.connect(
                lambda old, new: self._capture_split_cursor_position(new)
            )
        rect = self.ui.table.visualItemRect(item)
        self.split_float_btn.move(rect.right() - 28, rect.top() + 3)
        self.split_float_btn.raise_()
        self.split_float_btn.show()

    def _hide_split_float_button(self) -> None:
        if hasattr(self, "split_float_btn"):
            self.split_float_btn.hide()

    def _active_text_editor(self) -> Optional[QLineEdit]:
        focus_widget = QApplication.focusWidget()
        try:
            if isinstance(focus_widget, QLineEdit) and self._is_text_cell_editor(
                focus_widget
            ):
                return focus_widget
        except RuntimeError:
            pass

        for editor in self.ui.table.findChildren(QLineEdit):
            try:
                if editor.isVisible() and self._is_text_cell_editor(editor):
                    return editor
            except RuntimeError:
                continue
        return None

    def _capture_split_editor_state(self, editor: QLineEdit) -> None:
        try:
            self._split_editor_row = self.ui.table.currentRow()
            self._split_editor_text = editor.text()
            self._split_cursor_position = editor.cursorPosition()
        except RuntimeError:
            pass

    def _capture_split_editor_text(self, text: str) -> None:
        self._split_editor_text = text

    def _capture_split_cursor_position(self, cursor_position: int) -> None:
        self._split_cursor_position = cursor_position

    def _is_text_cell_editor(self, editor: QLineEdit) -> bool:
        row = self.ui.table.currentRow()
        item = self.ui.table.item(row, 3)
        if row < 0 or item is None:
            return False
        cell_rect = self.ui.table.visualItemRect(item)
        editor_center = editor.mapTo(self.ui.table.viewport(), editor.rect().center())
        return cell_rect.contains(editor_center)

    def _split_current_editor_text(self) -> None:
        row = (
            self._split_editor_row
            if self._split_editor_row is not None
            else self.ui.table.currentRow()
        )
        chunk = self._split_editor_chunk or self._chunk_for_row(row)
        if not chunk:
            return

        editor = self._active_text_editor()
        if editor is not None:
            self._capture_split_editor_state(editor)

        if not self._split_editor_text:
            QMessageBox.information(
                self,
                "Edit Text First",
                "Edit the transcript text and place the cursor where it should split.",
            )
            return

        cursor_position = self._split_cursor_position
        text = self._split_editor_text
        item = self.ui.table.item(row, 3)
        if item is not None:
            item.setText(text)
        chunk.text = text
        new_idx, new_chunk = self.viewmodel.split_chunk(chunk, cursor_position)
        if new_idx is None:
            QMessageBox.information(
                self,
                "Cannot Split",
                "Place the cursor between two text parts before splitting.",
            )
            return
        if editor is not None:
            editor.clearFocus()
        self._hide_split_float_button()
        self._split_editor_chunk = None
        self._split_editor_row = None
        self._split_editor_text = ""
        self._split_cursor_position = 0
        self.ui.table.blockSignals(True)
        self._update_chunk_row(row, chunk)
        if new_chunk is not None:
            self._insert_chunk_row(new_idx, new_chunk)
        self._refresh_row_indexes(row)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()

    def _merge_chunk(self, chunk: ExamSrtChunk):
        idx, _ = self.viewmodel.merge_chunk(chunk)
        if idx is None:
            return
        self._hide_split_float_button()
        self.ui.table.blockSignals(True)
        self._update_chunk_row(idx, chunk)
        self.ui.table.removeRow(idx + 1)
        self._refresh_row_indexes(idx)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()

    def _chunk_for_row(self, row: int) -> Optional[ExamSrtChunk]:
        if row < 0:
            return None
        idx_item = self.ui.table.item(row, 0)
        if idx_item is None:
            return None
        idx = int(idx_item.text())
        return next((c for c in self.viewmodel.srt_chunks if c.index == idx), None)

    def _row_for_chunk(self, chunk: ExamSrtChunk) -> Optional[int]:
        for row in range(self.ui.table.rowCount()):
            row_chunk = self._chunk_for_row(row)
            if row_chunk is chunk:
                return row
        return None
