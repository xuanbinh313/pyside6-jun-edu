# Import the icon management library.
from typing import Callable, Optional

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    def __init__(self, viewmodel:ExamDetailsViewModel , parent:Optional[QWidget]=None):
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
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
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

    def _context_label(self, ctx:ExamContext):
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
        parent:Optional[QWidget]=None,
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
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
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
    def __init__(self, value: float, on_change:Callable[[float], None], parent:Optional[QWidget]=None):
        super().__init__(parent)
        self.on_change = on_change
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Add a muted red minus icon.
        self.minus_btn = QPushButton()
        self.minus_btn.setFixedWidth(22)
        self.minus_btn.setIcon(qta.icon('fa5s.minus', color='#c53929'))
        self.minus_btn.clicked.connect(self._minus)
        layout.addWidget(self.minus_btn)
        
        self.val_edit = QLineEdit(f"{value:.3f}")
        self.val_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_edit.editingFinished.connect(self._text_changed)
        layout.addWidget(self.val_edit)
        
        # Add a blue plus icon.
        self.plus_btn = QPushButton()
        self.plus_btn.setFixedWidth(22)
        self.plus_btn.setIcon(qta.icon('fa5s.plus', color='#1a73e8'))
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
    def __init__(self, viewmodel:ExamDetailsViewModel , parent:Optional[QWidget]=None):
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
        
        self.setup_ui()
        
    def setup_ui(self):
        self.ui = Ui_ExamTranscriptWidget()
        self.ui.setupUi(self)
        
        # Configure the main Play/Pause button.
        self.ui.play_pause_btn.clicked.connect(self._toggle_play)
        self._update_play_pause_icon() # Initialize the icon.
        
        self.ui.add_to_question_btn.setIcon(qta.icon('fa5s.plus', color='white'))
        self.ui.add_to_question_btn.setIconSize(QSize(16, 16))
        self.ui.add_to_question_btn.setStyleSheet(
            "QPushButton { background-color: #34a853; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #dadce0; color: #5f6368; }"
            "QPushButton:hover:!disabled { background-color: #188038; }"
        )
        self.ui.add_to_question_btn.clicked.connect(self._on_add_to_question_clicked)

        self.auto_detect_audio_btn = QPushButton("Auto-detect Audio", self)
        self.auto_detect_audio_btn.setIcon(qta.icon('fa5s.robot', color='white'))
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
        
        self.ui.save_btn.setIcon(qta.icon('fa5s.save', color='white'))
        self.ui.save_btn.setIconSize(QSize(16, 16))
        self.ui.save_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
        self.ui.save_btn.clicked.connect(self._on_save_clicked)
        self.ui.save_btn.setVisible(False)
        
        self.ui.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.ui.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.table.itemChanged.connect(self._on_item_changed)
        self.ui.table.selectionModel().selectionChanged.connect(
            self._update_add_to_question_enabled
        )

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
            self.ui.play_pause_btn.setIcon(qta.icon('fa5s.pause', color='#d93025'))
            self.ui.play_pause_btn.setText(" Pause")
        else:
            self.ui.play_pause_btn.setIcon(qta.icon('fa5s.play', color='#1e8e3e'))
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

    def _on_slider_moved(self, value:int):
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
                if getattr(self, '_current_highlighted_row', None) != row:
                    self._set_playback_highlight(row)
                break

    def _set_playback_highlight(self, row:int):
        if self._current_highlighted_row is not None:
            self._set_row_background(self._current_highlighted_row, QBrush())
        self._set_row_background(row, QBrush(QColor("#e8f0fe")))
        self._current_highlighted_row = row

    def _set_row_background(self, row:int, brush:QBrush):
        for column in (0, 3):
            item = self.ui.table.item(row, column)
            if item:
                item.setBackground(brush)

    def _play_loop(self, loop_idx:int):
        if self.looping_chunk_idx != loop_idx:
            return 
        
        chunk = next((c for c in self.viewmodel.srt_chunks if c.index == loop_idx), None)
        if chunk:
            self.play_range(chunk.start_time, chunk.end_time, loop_idx)
            
    def play_range(self, start_time: float, end_time: float, loop_idx: Optional[int] = None):
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

    def _insert_chunk_row(self, row: int, chunk:ExamSrtChunk):
        self.ui.table.insertRow(row)
        
        idx_item = QTableWidgetItem(str(chunk.index))
        idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.ui.table.setItem(row, 0, idx_item)
        
        # Start Time
        start_w = TimeAdjustWidget(chunk.start_time, lambda v, c=chunk: self._update_time(c, 'start', v))
        self.ui.table.setCellWidget(row, 1, start_w)
        
        # End Time
        end_w = TimeAdjustWidget(chunk.end_time, lambda v, c=chunk: self._update_time(c, 'end', v))
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
        play_btn.setIcon(qta.icon('fa5s.play', color='#1e8e3e'))
        play_btn.setToolTip("Play Once")
        def on_play_clicked(c: ExamSrtChunk = chunk) -> None:
            self.play_range(c.start_time, c.end_time)
        play_btn.clicked.connect(on_play_clicked)
        action_layout.addWidget(play_btn)
        
        # 2. Loop segment button -> blue
        loop_btn = QPushButton()
        loop_btn.setFixedSize(16, 16)
        loop_btn.setIcon(qta.icon('fa5s.sync-alt', color='#1a73e8'))
        loop_btn.setToolTip("Loop")
        def on_loop_clicked(c: ExamSrtChunk = chunk) -> None:
            self._toggle_loop(c)
        loop_btn.clicked.connect(on_loop_clicked)
        action_layout.addWidget(loop_btn)
        
        # 3. Duplicate button -> amber
        dup_btn = QPushButton()
        dup_btn.setFixedSize(16, 16)
        dup_btn.setIcon(qta.icon('fa5s.copy', color='#f9ab00'))
        dup_btn.setToolTip("Duplicate")
        def on_duplicate_clicked(c: ExamSrtChunk = chunk) -> None:
            self._duplicate_chunk(c)
        dup_btn.clicked.connect(on_duplicate_clicked)
        action_layout.addWidget(dup_btn)
        
        # 4. Merge next row button -> dark gray
        merge_btn = QPushButton()
        merge_btn.setFixedSize(16, 16)
        merge_btn.setIcon(qta.icon('fa5s.compress-arrows-alt', color='#5f6368'))
        merge_btn.setToolTip("Merge Next")
        def on_merge_clicked(c: ExamSrtChunk = chunk) -> None:
            self._merge_chunk(c)
        merge_btn.clicked.connect(on_merge_clicked)
        action_layout.addWidget(merge_btn)
        
        self.ui.table.setCellWidget(row, 4, action_widget)

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self.ui.save_btn.setVisible(True)

    def _on_save_clicked(self):
        self.viewmodel.save_chunks()
        self._has_changes = False
        self.ui.save_btn.setVisible(False)

    def _selected_chunks(self) -> list[ExamSrtChunk]:
        chunks: list[ExamSrtChunk] = []
        rows = sorted({index.row() for index in self.ui.table.selectedIndexes()})
        for row in rows:
            idx_item = self.ui.table.item(row, 0)
            if idx_item is None:
                continue
            idx = int(idx_item.text())

            chunk:Optional[ExamSrtChunk] = next((c for c in self.viewmodel.srt_chunks if c.index == idx), None)
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
                ctx.id, float(first.start_time), float(last.end_time)
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
            context.id: self.viewmodel.context_question_numbers(context.id)
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

    def _update_time(self, chunk:ExamSrtChunk, field:str, value: float):
        if field == 'start':
            chunk.start_time = value
        elif field == 'end':
            chunk.end_time = value
        self._mark_changed()
            
    def _on_item_changed(self, item:QTableWidgetItem):
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
                
    def _toggle_loop(self, chunk: ExamSrtChunk):
        if self.looping_chunk_idx == chunk.index:
            self.looping_chunk_idx = None
            self.play_until = None
        else:
            self.play_range(chunk.start_time, chunk.end_time, chunk.index)
            
    def _duplicate_chunk(self, chunk:ExamSrtChunk):
        new_idx, new_chunk = self.viewmodel.duplicate_chunk(chunk)
        
        self.ui.table.blockSignals(True)
        self._insert_chunk_row(new_idx, new_chunk)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()

    def _merge_chunk(self, chunk:ExamSrtChunk):
        idx, _ = self.viewmodel.merge_chunk(chunk)
        if idx is None:
            return
            
        self.ui.table.blockSignals(True)
        idx_item = self.ui.table.item(idx, 3)
        if idx_item:
            idx_item.setText(chunk.text)
        end_widget = self.ui.table.cellWidget(idx, 2)
        if isinstance(end_widget, TimeAdjustWidget):
            end_widget.val_edit.setText(f"{chunk.end_time:.3f}")
        self.ui.table.removeRow(idx + 1)
        self.ui.table.blockSignals(False)
        self._update_add_to_question_enabled()
        self._mark_changed()
