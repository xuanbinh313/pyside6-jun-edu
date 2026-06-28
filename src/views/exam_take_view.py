import html

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from src.utils.qt import clear_layout
from ui_gen.ui_exam_take_view import Ui_ExamTakeView


class ExamTakeView(QWidget):
    def __init__(self, viewmodel, go_back_callback, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.go_back_callback = go_back_callback
        self._part_checks = []
        self._tag_checks = []
        self._answer_groups = {}
        self._current_analytics = None

        self.ui = Ui_ExamTakeView()
        self.ui.setupUi(self)
        self._setup_pages()
        self._connect_signals()
        self.viewmodel.load_exam()

    def _setup_pages(self):
        self.ui.timer_label.setVisible(False)
        self.ui.back_btn.clicked.connect(self._on_back_clicked)

        self.overview_page = QWidget()
        self.overview_layout = QVBoxLayout(self.overview_page)
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_layout.setSpacing(12)

        self.test_page = QWidget()
        self.test_layout = QVBoxLayout(self.test_page)
        self.test_layout.setContentsMargins(0, 0, 0, 0)
        self.test_layout.setSpacing(10)

        self.result_page = QWidget()
        self.result_layout = QVBoxLayout(self.result_page)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(10)

        self.history_page = QWidget()
        self.history_layout = QVBoxLayout(self.history_page)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(10)

        self.ui.stacked_widget.addWidget(self.overview_page)
        self.ui.stacked_widget.addWidget(self.test_page)
        self.ui.stacked_widget.addWidget(self.result_page)
        self.ui.stacked_widget.addWidget(self.history_page)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)

    def _connect_signals(self):
        self.viewmodel.data_loaded.connect(self._render_overview)
        self.viewmodel.test_started.connect(self._render_test)
        self.viewmodel.result_ready.connect(self._render_result)
        self.viewmodel.error_message.connect(self._show_error)

    def _render_overview(self):
        clear_layout(self.overview_layout)
        self._timer.stop()
        self.ui.timer_label.setVisible(False)
        self.ui.stacked_widget.setCurrentWidget(self.overview_page)

        exam = self.viewmodel.exam
        self.ui.title_label.setText(exam.title)
        question_count = len(self.viewmodel.questions)
        self.ui.subtitle_label.setText(
            f"{exam.duration_minutes} min | {len(self.viewmodel.parts)} parts | {question_count} questions"
        )

        if exam.description:
            description = QLabel(exam.description)
            description.setWordWrap(True)
            description.setStyleSheet("color: #3c4043; font-size: 13px;")
            self.overview_layout.addWidget(description)

        self.overview_layout.addWidget(self._history_table())
        self.overview_layout.addWidget(self._mode_tabs())
        self.overview_layout.addStretch(1)

    def _history_table(self):
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(box)

        title = QLabel("Previous Attempts")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Date", "Duration", "Score", "Accuracy", "View"])
        table.setRowCount(len(self.viewmodel.attempts))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

        for row, attempt in enumerate(self.viewmodel.attempts):
            table.setItem(row, 0, QTableWidgetItem(attempt.created_at.strftime("%Y-%m-%d %H:%M")))
            table.setItem(row, 1, QTableWidgetItem(self._format_seconds(attempt.duration_seconds)))
            table.setItem(row, 2, QTableWidgetItem(f"{attempt.total_correct}/{attempt.total_questions}"))
            table.setItem(row, 3, QTableWidgetItem(f"{attempt.accuracy:.1f}%"))
            view_btn = QPushButton()
            view_btn.setIcon(qta.icon("fa5s.eye", color="#1a73e8"))
            view_btn.setToolTip("View attempt summary")
            view_btn.clicked.connect(
                lambda checked=False, item=attempt: self._render_attempt_history(item)
            )
            table.setCellWidget(row, 4, view_btn)

        table.resizeColumnsToContents()
        layout.addWidget(table)
        return box

    def _mode_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(self._practice_tab(), "Practice")
        tabs.addTab(self._real_test_tab(), "Real Test")
        return tabs

    def _practice_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        part_label = QLabel("Parts")
        part_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(part_label)

        part_row = QHBoxLayout()
        self._part_checks = []
        for part in self.viewmodel.parts:
            check = QCheckBox(f"Part {part}")
            check.setChecked(True)
            check.setProperty("part", part)
            self._part_checks.append(check)
            part_row.addWidget(check)
        part_row.addStretch(1)
        layout.addLayout(part_row)

        tag_label = QLabel("Question Tags")
        tag_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(tag_label)

        tag_row = QHBoxLayout()
        self._tag_checks = []
        if self.viewmodel.tags:
            for tag in self.viewmodel.tags:
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
        start_btn.setStyleSheet(self._primary_button_style())
        start_btn.clicked.connect(self._start_practice)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _real_test_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        summary = QLabel(
            f"Full exam: {len(self.viewmodel.questions)} questions, "
            f"{self.viewmodel.exam.duration_minutes} minutes."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        start_btn = QPushButton("Start Real Test")
        start_btn.setIcon(qta.icon("fa5s.stopwatch", color="white"))
        start_btn.setStyleSheet(self._primary_button_style())
        start_btn.clicked.connect(lambda: self.viewmodel.start_test("real"))
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _render_test(self):
        clear_layout(self.test_layout)
        self._answer_groups = {}
        self.ui.stacked_widget.setCurrentWidget(self.test_page)
        self.ui.timer_label.setVisible(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        questions_layout = QVBoxLayout(container)
        questions_layout.setSpacing(10)

        for question in self.viewmodel.active_questions:
            card = self._question_card(question)
            questions_layout.addWidget(card)
        questions_layout.addStretch(1)
        scroll.setWidget(container)
        self.test_layout.addWidget(scroll)

        footer = QHBoxLayout()
        footer.addStretch(1)
        submit_btn = QPushButton("Submit")
        submit_btn.setIcon(qta.icon("fa5s.check", color="white"))
        submit_btn.setStyleSheet(self._primary_button_style())
        submit_btn.clicked.connect(self._submit_test)
        footer.addWidget(submit_btn)
        self.test_layout.addLayout(footer)

        self._timer.start()
        self._on_timer_tick()

    def _question_card(self, question):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        header = QLabel(f"Part {question.part} | Question {question.question_number}")
        header.setStyleSheet("font-weight: bold; color: #1a73e8;")
        layout.addWidget(header)

        if question.context_text:
            context = QLabel(question.context_text)
            context.setTextFormat(Qt.TextFormat.PlainText)
            context.setWordWrap(True)
            context.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            context.setStyleSheet(
                "QLabel { border: 1px solid #dadce0; border-radius: 6px; "
                "background-color: #fffde7; padding: 10px; color: #202124; "
                "font-size: 13px; line-height: 1.5; }"
            )
            layout.addWidget(context)

        stem = QLabel(html.escape(question.content))
        stem.setTextFormat(Qt.TextFormat.RichText)
        stem.setWordWrap(True)
        stem.setStyleSheet("font-size: 13px; color: #202124;")
        layout.addWidget(stem)

        group = QButtonGroup(card)
        group.setExclusive(True)
        for option in question.options:
            radio = QRadioButton(f"{option.display_letter}. {option.text}")
            radio.setProperty("display_index", option.display_index)
            radio.toggled.connect(
                lambda checked, qid=question.question_id, idx=option.display_index: (
                    self.viewmodel.submit_answer(qid, idx) if checked else None
                )
            )
            group.addButton(radio, option.display_index)
            layout.addWidget(radio)
        self._answer_groups[question.question_id] = group

        if self.viewmodel.mode == "practice":
            skip_btn = QPushButton("Skip")
            skip_btn.setIcon(qta.icon("fa5s.forward", color="#5f6368"))
            skip_btn.clicked.connect(lambda checked=False, qid=question.question_id, g=group: self._skip_question(qid, g))
            layout.addWidget(skip_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        return card

    def _render_result(self):
        clear_layout(self.result_layout)
        self._timer.stop()
        self.ui.timer_label.setVisible(False)
        self.ui.stacked_widget.setCurrentWidget(self.result_page)

        score = QLabel(
            f"Score: {self.viewmodel.total_correct} / {len(self.viewmodel.active_questions)} "
            f"({self.viewmodel.final_score:.1f}%)"
        )
        score.setStyleSheet("font-size: 18px; font-weight: bold; color: #202124;")
        self.result_layout.addWidget(score)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        for question in self.viewmodel.active_questions:
            layout.addWidget(self._result_card(question))
        layout.addStretch(1)
        scroll.setWidget(container)
        self.result_layout.addWidget(scroll)

        done_btn = QPushButton("Back to Exam")
        done_btn.clicked.connect(self._render_overview)
        self.result_layout.addWidget(done_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _render_attempt_history(self, attempt):
        analytics = self.viewmodel.load_attempt_analytics(attempt.id)
        if analytics is None:
            return

        self._current_analytics = analytics
        clear_layout(self.history_layout)
        self.ui.stacked_widget.setCurrentWidget(self.history_page)
        self.ui.timer_label.setVisible(False)
        self.ui.title_label.setText("Attempt Analytics")
        self.ui.subtitle_label.setText(
            analytics.summary.created_at.strftime("%Y-%m-%d %H:%M")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        layout.addLayout(self._analytics_kpi_row(analytics))
        layout.addWidget(self._breakdown_tabs(analytics))

        answer_title = QLabel("Answer Sheet")
        answer_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #202124;")
        layout.addWidget(answer_title)
        layout.addWidget(self._answer_sheet(analytics.answers))

        footer = QHBoxLayout()
        retake_btn = QPushButton("Retake Wrong Answers")
        retake_btn.setIcon(qta.icon("fa5s.redo", color="white"))
        retake_btn.setStyleSheet(self._primary_button_style())
        retake_btn.clicked.connect(lambda: self._retake_wrong_answers(analytics))
        footer.addWidget(retake_btn)
        footer.addStretch(1)
        layout.addLayout(footer)

        scroll.setWidget(container)
        self.history_layout.addWidget(scroll)

    def _analytics_kpi_row(self, analytics):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(
            self._kpi_card(
                "Metrics",
                [
                    f"Results: {analytics.total_correct} / {analytics.summary.total_questions}",
                    f"Accuracy: {analytics.accuracy_rate:.1f}%",
                    f"Time: {self._format_hms(analytics.summary.duration_seconds)}",
                ],
                "#ffffff",
            ),
            2,
        )
        row.addWidget(self._counter_card("Correct", analytics.total_correct, "#e6f4ea", "#28a745"))
        row.addWidget(self._counter_card("Wrong", analytics.total_wrong, "#fce8e6", "#dc3545"))
        row.addWidget(self._counter_card("Skipped", analytics.total_unanswered, "#f1f3f4", "#6c757d"))
        return row

    def _kpi_card(self, title, lines, background):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"QFrame {{ background: {background}; border-radius: 6px; }}")
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(label)
        for line in lines:
            item = QLabel(line)
            item.setStyleSheet("color: #3c4043;")
            layout.addWidget(item)
        return card

    def _counter_card(self, title, value, background, color):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"QFrame {{ background: {background}; border-radius: 6px; }}")
        layout = QVBoxLayout(card)
        value_label = QLabel(str(value))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return card

    def _breakdown_tabs(self, analytics):
        tabs = QTabWidget()
        tabs.addTab(self._breakdown_table(analytics.overall_breakdown), "Overall")
        for part, breakdown in analytics.part_breakdowns.items():
            tabs.addTab(self._breakdown_table(breakdown), f"Part {part}")
        return tabs

    def _breakdown_table(self, breakdown_rows):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Question Category", "Correct", "Wrong", "Skipped", "Accuracy %", "Questions"]
        )
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(breakdown_rows))
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        for column in (1, 2, 3, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 180)

        for row, breakdown in enumerate(breakdown_rows):
            table.setItem(row, 0, QTableWidgetItem(breakdown.name))
            table.setItem(row, 1, QTableWidgetItem(str(breakdown.correct)))
            table.setItem(row, 2, QTableWidgetItem(str(breakdown.wrong)))
            table.setItem(row, 3, QTableWidgetItem(str(breakdown.skipped)))
            table.setItem(row, 4, QTableWidgetItem(f"{breakdown.accuracy:.1f}%"))
            table.setCellWidget(row, 5, self._question_badges(breakdown.answers))

        table.resizeRowsToContents()
        for row, breakdown in enumerate(breakdown_rows):
            table.setRowHeight(row, self._badge_list_height(len(breakdown.answers)))
        table.setFixedHeight(self._table_content_height(table))
        return table

    def _question_badges(self, answers):
        list_widget = QListWidget()
        list_widget.setViewMode(QListView.ViewMode.IconMode)
        list_widget.setFlow(QListView.Flow.LeftToRight)
        list_widget.setWrapping(True)
        list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        list_widget.setMovement(QListView.Movement.Static)
        list_widget.setSpacing(4)
        list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_widget.setToolTip(f"{len(answers)} question badge(s)")
        list_widget.setStyleSheet(
            "QListWidget { background: transparent; border: none; }"
            "QListWidget::item { background: transparent; border: none; }"
        )
        list_widget.setFixedHeight(self._badge_list_height(len(answers)))

        for answer in answers:
            item = QListWidgetItem()
            item.setSizeHint(QSize(38, 28))
            list_widget.addItem(item)

            badge = QPushButton(str(answer.question_number))
            badge.setFixedSize(34, 24)
            badge.setStyleSheet(self._answer_badge_style(answer))
            badge.clicked.connect(lambda checked=False, item=answer: self._show_answer_dialog(item))
            list_widget.setItemWidget(item, badge)

        return list_widget

    def _badge_list_height(self, answer_count):
        if answer_count <= 0:
            return 34
        rows = ((answer_count - 1) // 8) + 1
        return rows * 32 + 6

    def _table_content_height(self, table):
        header_height = table.horizontalHeader().height()
        rows_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        frame_height = table.frameWidth() * 2
        return header_height + rows_height + frame_height + 4

    def _answer_sheet(self, answers):
        sheet = QWidget()
        grid = QGridLayout(sheet)
        grid.setSpacing(8)
        columns = 3
        for index, answer in enumerate(answers):
            tile = self._answer_tile(answer)
            grid.addWidget(tile, index // columns, index % columns)
        return sheet

    def _answer_tile(self, answer):
        tile = QFrame()
        tile.setFrameShape(QFrame.Shape.StyledPanel)
        tile.setStyleSheet("QFrame { background: #ffffff; border-radius: 6px; }")
        layout = QHBoxLayout(tile)

        user_text = answer.user_choice or "not answered"
        label = QLabel(
            f"Q{answer.question_number}  Key {answer.correct_answer}: {user_text}"
        )
        if answer.is_unanswered:
            label.setStyleSheet("color: #6c757d; font-style: italic;")
        else:
            label.setStyleSheet("color: #202124;")
        layout.addWidget(label, 1)

        details_btn = QPushButton("Details")
        details_btn.clicked.connect(lambda checked=False, item=answer: self._show_answer_dialog(item))
        layout.addWidget(details_btn)
        return tile

    def _show_answer_dialog(self, answer):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Question {answer.question_number}")
        dialog.resize(760, 520)
        layout = QVBoxLayout(dialog)

        context = QLabel(answer.context_text or "No context saved.")
        context.setTextFormat(Qt.TextFormat.PlainText)
        context.setWordWrap(True)
        context.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        context.setStyleSheet(
            "QLabel { border: 1px solid #dadce0; border-radius: 6px; "
            "background-color: #fffde7; padding: 10px; color: #202124; }"
        )
        layout.addWidget(context)

        question = QLabel(f"Q{answer.question_number}. {answer.content}")
        question.setWordWrap(True)
        question.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(question)

        user_choice = answer.user_choice or "not answered"
        details = QLabel(
            f"Your answer: {user_choice} {answer.user_text}\n"
            f"Correct answer: {answer.correct_answer} {answer.correct_text}"
        )
        details.setWordWrap(True)
        layout.addWidget(details)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _retake_wrong_answers(self, analytics):
        wrong_ids = [
            answer.question_id
            for answer in analytics.answers
            if not answer.is_correct
        ]
        if not wrong_ids:
            QMessageBox.information(self, "Retake", "There are no wrong or skipped answers to retake.")
            return
        self.viewmodel.start_review_questions(wrong_ids)

    def _result_card(self, question):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)

        status = "Correct" if question.is_correct else "Wrong"
        color = "#34a853" if question.is_correct else "#ea4335"
        title = QLabel(f"Question {question.question_number}: {status}")
        title.setStyleSheet(f"font-weight: bold; color: {color};")
        layout.addWidget(title)

        stem = QLabel(question.content)
        stem.setWordWrap(True)
        layout.addWidget(stem)

        user_choice = question.user_choice or "Unanswered"
        details = QLabel(
            f"Your answer: {user_choice}\n"
            f"Correct answer: {question.correct_answer}\n"
            f"Correct text: {question.correct_text}"
        )
        details.setWordWrap(True)
        layout.addWidget(details)
        return card

    def _start_practice(self):
        selected_parts = [
            check.property("part")
            for check in self._part_checks
            if check.isChecked()
        ]
        selected_tags = [
            check.property("tag")
            for check in self._tag_checks
            if check.isChecked()
        ]
        self.viewmodel.start_test("practice", selected_parts, selected_tags)

    def _skip_question(self, question_id, group):
        group.setExclusive(False)
        for button in group.buttons():
            button.setChecked(False)
        group.setExclusive(True)
        self.viewmodel.skip_question(question_id)

    def _submit_test(self):
        self._timer.stop()
        self.viewmodel.complete_test()

    def _on_timer_tick(self):
        remaining = self.viewmodel.real_test_remaining_seconds()
        if remaining is None:
            self.ui.timer_label.setText(f"Elapsed {self._format_seconds(self.viewmodel.elapsed_seconds())}")
            return
        self.ui.timer_label.setText(f"Remaining {self._format_seconds(remaining)}")
        if remaining <= 0:
            self._submit_test()

    def _on_back_clicked(self):
        if self.ui.stacked_widget.currentWidget() == self.test_page:
            confirm = QMessageBox.question(
                self,
                "Leave Test",
                "Leave this test without saving a result?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self._timer.stop()
        if self.ui.stacked_widget.currentWidget() in (self.history_page, self.result_page):
            self._render_overview()
            return
        self.go_back_callback()

    def _show_error(self, message):
        QMessageBox.warning(self, "Exam", message)

    def _format_seconds(self, seconds):
        minutes, secs = divmod(max(0, int(seconds)), 60)
        return f"{minutes:02d}:{secs:02d}"

    def _format_hms(self, seconds):
        hours, remainder = divmod(max(0, int(seconds)), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"

    def _answer_badge_style(self, answer):
        if answer.is_correct:
            return (
                "QPushButton { background-color: #28a745; color: white; "
                "border: none; border-radius: 4px; font-weight: bold; }"
            )
        if answer.is_unanswered:
            return (
                "QPushButton { background-color: #f8f9fa; color: #6c757d; "
                "border: 1px solid #6c757d; border-radius: 4px; font-weight: bold; }"
            )
        return (
            "QPushButton { background-color: #dc3545; color: white; "
            "border: none; border-radius: 4px; font-weight: bold; }"
        )

    def _primary_button_style(self):
        return (
            "QPushButton { background-color: #1a73e8; color: white; "
            "font-weight: bold; border-radius: 4px; padding: 7px 14px; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
