from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidgetItem, QHeaderView,
                               QLineEdit, QAbstractItemView)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Qt, QTimer, QFile, QSize
from PySide6.QtUiTools import QUiLoader
import os
# 1. Import thư viện quản lý icon
import qtawesome as qta

class TimeAdjustWidget(QWidget):
    def __init__(self, value, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Thêm icon Minus (Dấu trừ) màu đỏ trầm
        self.minus_btn = QPushButton()
        self.minus_btn.setFixedWidth(22)
        self.minus_btn.setIcon(qta.icon('fa5s.minus', color='#c53929'))
        self.minus_btn.clicked.connect(self._minus)
        layout.addWidget(self.minus_btn)
        
        self.val_edit = QLineEdit(f"{value:.3f}")
        self.val_edit.setAlignment(Qt.AlignCenter)
        self.val_edit.editingFinished.connect(self._text_changed)
        layout.addWidget(self.val_edit)
        
        # Thêm icon Plus (Dấu cộng) màu xanh dương
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
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        # Lắng nghe trạng thái media để cập nhật icon Play/Pause tự động
        self.player.playbackStateChanged.connect(self._update_play_pause_icon)
        
        self.play_until = None
        self.looping_chunk_idx = None
        self._current_highlighted_row = None
        self._has_changes = False
        
        self.setup_ui()
        
    def setup_ui(self):
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(__file__), "../ui/exam_transcript_widget.ui")
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        
        # Cấu hình nút Play/Pause chính
        self.play_pause_btn = self.ui.play_pause_btn
        self.play_pause_btn.clicked.connect(self._toggle_play)
        self._update_play_pause_icon() # Khởi tạo icon ban đầu
        
        self.delay_spin = self.ui.delay_spin
        
        self.save_btn = self.ui.save_btn
        self.save_btn.setIcon(qta.icon('fa5s.save', color='white'))
        self.save_btn.setIconSize(QSize(16, 16))
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; "
            "padding: 4px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setVisible(False)
        
        self.table = self.ui.table
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemChanged.connect(self._on_item_changed)

        # Seek bar
        self.seek_slider = self.ui.seek_slider
        self.seek_slider.setTracking(False)  # only emit on release
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        self._slider_dragging = False

        self.time_current_label = self.ui.time_current_label
        self.time_total_label = self.ui.time_total_label

        self.seek_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #dadce0; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #1a73e8; border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -4px 0;"
            " background: #1a73e8; border-radius: 7px; }"
        )
        
    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _update_play_pause_icon(self):
        """Tự động thay đổi thiết kế nút Play/Pause bằng Python"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.play_pause_btn.setIcon(qta.icon('fa5s.pause', color='#d93025'))
            self.play_pause_btn.setText(" Tạm dừng")
        else:
            self.play_pause_btn.setIcon(qta.icon('fa5s.play', color='#1e8e3e'))
            self.play_pause_btn.setText(" Phát nhạc")
        self.play_pause_btn.setIconSize(QSize(16, 16))
            
    @staticmethod
    def _fmt_time(ms):
        # s = int(ms / 1000)
        # m, s = divmod(s, 60)
        return f"{ms / 1000.0:.3f}"

    def _on_duration_changed(self, duration_ms):
        self.seek_slider.setMaximum(max(duration_ms, 1))
        self.time_total_label.setText(self._fmt_time(duration_ms))

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_moved(self, value):
        self.time_current_label.setText(self._fmt_time(value))

    def _on_slider_released(self):
        self._slider_dragging = False
        self.player.setPosition(self.seek_slider.value())

    def _on_position_changed(self, pos_ms):
        if self.play_until and pos_ms >= self.play_until:
            self.player.pause()
            
            loop_idx = self.looping_chunk_idx
            self.play_until = None
            
            if loop_idx is not None:
                delay_ms = self.delay_spin.value() * 1000
                QTimer.singleShot(delay_ms, lambda: self._play_loop(loop_idx))

        # Update seek slider & time label (skip if user is dragging)
        if not self._slider_dragging:
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(pos_ms)
            self.seek_slider.blockSignals(False)
            self.time_current_label.setText(self._fmt_time(pos_ms))

        pos_sec = pos_ms / 1000.0
        for row, chunk in enumerate(self.viewmodel.srt_chunks):
            if chunk.start_time <= pos_sec <= chunk.end_time:
                if getattr(self, '_current_highlighted_row', None) != row:
                    self.table.selectRow(row)
                    self._current_highlighted_row = row
                break

    def _play_loop(self, loop_idx):
        if self.looping_chunk_idx != loop_idx:
            return 
        
        chunk = next((c for c in self.viewmodel.srt_chunks if c.index == loop_idx), None)
        if chunk:
            self.play_range(chunk.start_time, chunk.end_time, loop_idx)
            
    def play_range(self, start_time, end_time, loop_idx=None):
        self.looping_chunk_idx = loop_idx
        if loop_idx is not None:
            self.play_until = int(end_time * 1000)
        self.player.setPosition(int(start_time * 1000))
        self.player.play()
        
    def populate(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._has_changes = False
        self.save_btn.setVisible(False)
        
        if self.viewmodel.exam and self.viewmodel.exam.full_audio_url:
            path = self.viewmodel.exam.full_audio_url
            if os.path.exists(path):
                self.player.setSource(QUrl.fromLocalFile(path))
            elif path.startswith("http"):
                self.player.setSource(QUrl(path))
                
        for row, chunk in enumerate(self.viewmodel.srt_chunks):
            self._insert_chunk_row(row, chunk)
            
        self.table.blockSignals(False)

    def _insert_chunk_row(self, row, chunk):
        self.table.insertRow(row)
        
        idx_item = QTableWidgetItem(str(chunk.index))
        idx_item.setFlags(idx_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, idx_item)
        
        # Start Time
        start_w = TimeAdjustWidget(chunk.start_time, lambda v, c=chunk: self._update_time(c, 'start', v))
        self.table.setCellWidget(row, 1, start_w)
        
        # End Time
        end_w = TimeAdjustWidget(chunk.end_time, lambda v, c=chunk: self._update_time(c, 'end', v))
        self.table.setCellWidget(row, 2, end_w)
        
        # Text
        text_item = QTableWidgetItem(chunk.text)
        self.table.setItem(row, 3, text_item)
        
        # --- THÊM BỘ ICON CHO CÁC NÚT THAO TÁC TRÊN TỪNG DÒNG ---
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)
        
        # 1. Nút Nghe Thử (Play Once) -> Màu xanh lá
        play_btn = QPushButton()
        play_btn.setFixedSize(16, 16)
        play_btn.setIcon(qta.icon('fa5s.play', color='#1e8e3e'))
        play_btn.setToolTip("Play Once")
        play_btn.clicked.connect(lambda checked, c=chunk: self.play_range(c.start_time, c.end_time))
        action_layout.addWidget(play_btn)
        
        # 2. Nút Lặp đoạn (Loop) -> Màu xanh dương
        loop_btn = QPushButton()
        loop_btn.setFixedSize(16, 16)
        loop_btn.setIcon(qta.icon('fa5s.sync-alt', color='#1a73e8'))
        loop_btn.setToolTip("Loop")
        loop_btn.clicked.connect(lambda checked, c=chunk: self._toggle_loop(c))
        action_layout.addWidget(loop_btn)
        
        # 3. Nút Nhân đôi (Duplicate) -> Màu cam vàng
        dup_btn = QPushButton()
        dup_btn.setFixedSize(16, 16)
        dup_btn.setIcon(qta.icon('fa5s.copy', color='#f9ab00'))
        dup_btn.setToolTip("Duplicate")
        dup_btn.clicked.connect(lambda checked, c=chunk: self._duplicate_chunk(c))
        action_layout.addWidget(dup_btn)
        
        # 4. Nút Gộp dòng (Merge Next) -> Màu xám đen
        merge_btn = QPushButton()
        merge_btn.setFixedSize(16, 16)
        merge_btn.setIcon(qta.icon('fa5s.compress-arrows-alt', color='#5f6368'))
        merge_btn.setToolTip("Merge Next")
        merge_btn.clicked.connect(lambda checked, c=chunk: self._merge_chunk(c))
        action_layout.addWidget(merge_btn)
        
        self.table.setCellWidget(row, 4, action_widget)

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self.save_btn.setVisible(True)

    def _on_save_clicked(self):
        self.viewmodel.save_chunks()
        self._has_changes = False
        self.save_btn.setVisible(False)

    def _update_time(self, chunk, field, value):
        if field == 'start':
            chunk.start_time = value
        elif field == 'end':
            chunk.end_time = value
        self._mark_changed()
            
    def _on_item_changed(self, item):
        if item.column() == 3: 
            row = item.row()
            idx_str = self.table.item(row, 0).text()
            idx = int(idx_str)
            chunk = next((c for c in self.viewmodel.srt_chunks if c.index == idx), None)
            if chunk:
                chunk.text = item.text()
                self._mark_changed()
                
    def _toggle_loop(self, chunk):
        if self.looping_chunk_idx == chunk.index:
            self.looping_chunk_idx = None
            self.play_until = None
        else:
            self.play_range(chunk.start_time, chunk.end_time, chunk.index)
            
    def _duplicate_chunk(self, chunk):
        new_idx, new_chunk = self.viewmodel.duplicate_chunk(chunk)
        
        self.table.blockSignals(True)
        self._insert_chunk_row(new_idx, new_chunk)
        self.table.blockSignals(False)
        self._mark_changed()

    def _merge_chunk(self, chunk):
        idx, next_chunk = self.viewmodel.merge_chunk(chunk)
        if idx is None:
            return
            
        self.table.blockSignals(True)
        self.table.item(idx, 3).setText(chunk.text)
        end_w = self.table.cellWidget(idx, 2)
        end_w.val_edit.setText(f"{chunk.end_time:.3f}")
        
        self.table.removeRow(idx + 1)
        self.table.blockSignals(False)
        self._mark_changed()