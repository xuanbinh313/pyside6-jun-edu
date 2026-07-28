from typing import Callable, Optional

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from src.viewmodels.exam_take_viewmodel import AttemptSummary, ExamTakeViewModel


class AttemptHistoryWidget(QFrame):
    def __init__(
        self,
        attempts: list[AttemptSummary],
        on_view_attempt: Callable[[AttemptSummary], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._attempts = attempts
        self._on_view_attempt = on_view_attempt
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Previous Attempts")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["Date", "Duration", "Score", "Accuracy", "Parts", "Question Tags", "View"]
        )
        table.setRowCount(len(self._attempts))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

        for row, attempt in enumerate(self._attempts):
            table.setItem(
                row, 0, QTableWidgetItem(attempt.created_at.strftime("%Y-%m-%d %H:%M"))
            )
            table.setItem(row, 1, QTableWidgetItem(_format_seconds(attempt.duration_seconds)))
            table.setItem(
                row,
                2,
                QTableWidgetItem(f"{attempt.total_correct}/{attempt.total_questions}"),
            )
            table.setItem(row, 3, QTableWidgetItem(f"{attempt.accuracy:.1f}%"))
            table.setItem(row, 4, QTableWidgetItem(_parts_text(attempt.selected_parts)))
            table.setItem(row, 5, QTableWidgetItem(_tags_text(attempt.question_tags)))

            view_btn = QPushButton()
            view_btn.setIcon(qta.icon("fa5s.eye", color="#1a73e8"))
            view_btn.setToolTip("View attempt summary")
            view_btn.clicked.connect(
                lambda checked=False, item=attempt: self._on_view_attempt(item)
            )
            table.setCellWidget(row, 6, view_btn)

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)


class ExamTakeModeTabs(QTabWidget):
    def __init__(
        self,
        viewmodel: ExamTakeViewModel,
        on_start_practice: Callable[[list[int], list[str]], None],
        on_start_real: Callable[[], None],
        on_start_dictation: Callable[[], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._on_start_practice = on_start_practice
        self._on_start_real = on_start_real
        self._on_start_dictation = on_start_dictation
        self._part_checks: list[QCheckBox] = []
        self._tag_checks: list[QCheckBox] = []

        self.addTab(self._practice_tab(), "Practice")
        self.addTab(self._real_test_tab(), "Real Test")
        self.addTab(self._dictation_tab(), "Dictation")

    def _practice_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        part_label = QLabel("Parts")
        part_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(part_label)

        part_row = QHBoxLayout()
        for part in self._viewmodel.parts:
            check = QCheckBox(f"Part {part}")
            check.setProperty("part", part)
            self._part_checks.append(check)
            part_row.addWidget(check)
        part_row.addStretch(1)
        layout.addLayout(part_row)

        tag_label = QLabel("Question Tags")
        tag_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(tag_label)

        tag_row = QHBoxLayout()
        if self._viewmodel.tags:
            for tag in self._viewmodel.tags:
                check = QCheckBox(tag)
                check.setProperty("tag", tag)
                self._tag_checks.append(check)
                tag_row.addWidget(check)
        else:
            empty = QLabel("No tags yet")
            empty.setStyleSheet("color: #5f6368;")
            tag_row.addWidget(empty)
        tag_row.addStretch(1)
        layout.addLayout(tag_row)

        start_btn = QPushButton("Start Practice")
        start_btn.setIcon(qta.icon("fa5s.play", color="white"))
        start_btn.setStyleSheet(_primary_button_style())
        start_btn.clicked.connect(self._start_practice)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _real_test_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        exam = self._viewmodel.exam
        summary = QLabel(
            f"Full exam: {len(self._viewmodel.questions)} questions, "
            f"{exam.duration_minutes if exam else 0} minutes."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        start_btn = QPushButton("Start Real Test")
        start_btn.setIcon(qta.icon("fa5s.stopwatch", color="white"))
        start_btn.setStyleSheet(_primary_button_style())
        start_btn.clicked.connect(lambda: self._on_start_real())
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _dictation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        chunk_count = len(self._viewmodel.srt_chunks)
        audio_ready = bool(self._viewmodel.exam and self._viewmodel.exam.audio_name)
        summary = QLabel(
            f"{chunk_count} transcript chunk(s) available for listening practice."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if not chunk_count:
            warning = QLabel("Attach or import a transcript before starting dictation.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #d93025; font-weight: bold;")
            layout.addWidget(warning)
        if not audio_ready:
            warning = QLabel("This exam has no audio file, so playback is unavailable.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #d93025; font-weight: bold;")
            layout.addWidget(warning)

        start_btn = QPushButton("Start Dictation")
        start_btn.setIcon(qta.icon("fa5s.headphones", color="white"))
        start_btn.setStyleSheet(_primary_button_style())
        start_btn.setEnabled(bool(chunk_count and audio_ready))
        start_btn.clicked.connect(lambda: self._on_start_dictation())
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _start_practice(self) -> None:
        selected_parts = [
            int(check.property("part")) for check in self._part_checks if check.isChecked()
        ]
        selected_tags = [
            str(check.property("tag")) for check in self._tag_checks if check.isChecked()
        ]
        self._on_start_practice(selected_parts, selected_tags)


def _format_seconds(seconds: float) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


def _parts_text(parts: list[int]) -> str:
    if not parts:
        return "All"
    return ", ".join(f"Part {part}" for part in parts)


def _tags_text(tags: list[str]) -> str:
    if not tags:
        return "Untagged"
    return ", ".join(tags)


def _primary_button_style() -> str:
    return (
        "QPushButton { background-color: #1a73e8; color: white; "
        "font-weight: bold; border-radius: 4px; padding: 7px 14px; }"
        "QPushButton:hover { background-color: #1558b0; }"
    )
