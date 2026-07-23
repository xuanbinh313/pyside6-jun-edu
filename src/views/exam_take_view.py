from src.models.exam import ExamQuestion
from src.viewmodels.exam_take_viewmodel import AttemptSummary
from src.viewmodels.exam_take_viewmodel import AttemptAnalytics
from src.viewmodels.exam_take_viewmodel import AttemptAnswerDetail
import html
from typing import Callable, Optional, cast

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
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
from src.models.exam import ExamContext
from src.utils.helpers import get_local_media_path
from src.utils.qt import clear_layout
from src.viewmodels.exam_take_viewmodel import ExamTakeViewModel
from src.views.components.exam_context_html import context_content_html
from src.views.components.exam_context_section import (
    ExamContextSection,
    context_audio_range,
)
from src.views.components.option_question_item import OptionVocabularyTextBrowser
from src.views.components.tag_menu_dialog import TagMenuDialog
from src.views.exercise_dictation_view import ExerciseDictationView
from ui_gen.ui_exam_take_view import Ui_ExamTakeView


class ExamTakeView(QWidget):
    def __init__(
        self,
        viewmodel: ExamTakeViewModel,
        go_back_callback: Callable[[], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.viewmodel: ExamTakeViewModel = viewmodel
        self.go_back_callback: Callable[[], None] = go_back_callback
        self._part_checks: list[QCheckBox] = []
        self._tag_checks: list[QCheckBox] = []
        self._answer_groups: dict[str, QButtonGroup] = {}
        self._current_analytics = None
        self._dictation_view: Optional[ExerciseDictationView] = None
        self._current_test_part: Optional[int] = None
        self._context_map: dict[str, ExamContext] = {}
        self._question_widgets: dict[int, QWidget] = {}

        self.ui = Ui_ExamTakeView()
        self.ui.setupUi(self)
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.play_until: Optional[int] = None
        self.player.positionChanged.connect(self._on_audio_position_changed)
        self._setup_pages()
        self._connect_signals()
        self.viewmodel.load_exam()

    def _setup_pages(self):
        self.ui.timer_label.setVisible(False)
        self.ui.back_btn.clicked.connect(self._on_back_clicked)
        self.ui.part_list.currentItemChanged.connect(self._on_part_selection_changed)

        self.overview_page = self.ui.overview_page
        self.overview_layout = self.ui.overview_layout
        self.overview_layout.setSpacing(12)

        self.test_page = self.ui.test_page
        self.test_layout = self.ui.test_layout
        self.test_layout.setSpacing(10)

        self.result_page = self.ui.result_page
        self.result_layout = self.ui.result_layout
        self.result_layout.setSpacing(10)

        self.history_page = self.ui.history_page
        self.history_layout = self.ui.history_layout
        self.history_layout.setSpacing(10)

        self.dictation_page = self.ui.dictation_page
        self.dictation_layout = self.ui.dictation_layout
        self.dictation_layout.setSpacing(10)

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
        self.ui.title_label.setText(exam.title if exam else "")
        question_count = len(self.viewmodel.questions)
        self.ui.subtitle_label.setText(
            f"{exam.duration_minutes if exam else 0} min | {len(self.viewmodel.parts)} parts | {question_count} questions"
        )

        if exam and exam.description:
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
        table.setHorizontalHeaderLabels(
            ["Date", "Duration", "Score", "Accuracy", "View"]
        )
        table.setRowCount(len(self.viewmodel.attempts))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)

        for row, attempt in enumerate(self.viewmodel.attempts):
            table.setItem(
                row, 0, QTableWidgetItem(attempt.created_at.strftime("%Y-%m-%d %H:%M"))
            )
            table.setItem(
                row, 1, QTableWidgetItem(self._format_seconds(attempt.duration_seconds))
            )
            table.setItem(
                row,
                2,
                QTableWidgetItem(f"{attempt.total_correct}/{attempt.total_questions}"),
            )
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
        tabs.addTab(self._dictation_tab(), "Dictation")
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

        exam = self.viewmodel.exam
        summary = QLabel(
            f"Full exam: {len(self.viewmodel.questions)} questions, "
            f"{exam.duration_minutes if exam else 0} minutes."
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

    def _dictation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        chunk_count = len(self.viewmodel.srt_chunks)
        audio_ready = bool(self.viewmodel.exam and self.viewmodel.exam.audio_name)
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
        start_btn.setStyleSheet(self._primary_button_style())
        start_btn.setEnabled(bool(chunk_count and audio_ready))
        start_btn.clicked.connect(self._start_dictation)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _start_dictation(self):
        clear_layout(self.dictation_layout)
        self._dictation_view = ExerciseDictationView(
            self.viewmodel.srt_chunks,
            self.viewmodel.exam.audio_name if self.viewmodel.exam else None,
            self,
        )
        self.dictation_layout.addWidget(self._dictation_view)
        self.ui.stacked_widget.setCurrentWidget(self.dictation_page)
        self.ui.timer_label.setVisible(False)
        self.ui.title_label.setText("Dictation")
        self.ui.subtitle_label.setText("Listen, type, and compare each transcript chunk")
        self._dictation_view.start()

    def _render_test(self):
        self._answer_groups = {}
        self._context_map = {ctx.id: ctx for ctx in self.viewmodel.contexts}
        self.ui.stacked_widget.setCurrentWidget(self.test_page)
        self.ui.timer_label.setVisible(True)
        self._populate_test_parts()
        self._render_test_questions()

        clear_layout(self.ui.test_footer_layout)
        footer = self.ui.test_footer_layout
        footer.addStretch(1)
        submit_btn = QPushButton("Submit")
        submit_btn.setIcon(qta.icon("fa5s.check", color="white"))
        submit_btn.setStyleSheet(self._primary_button_style())
        submit_btn.clicked.connect(self._submit_test)
        footer.addWidget(submit_btn)

        self._timer.start()
        self._on_timer_tick()

    def _populate_test_parts(self):
        self.ui.part_list.blockSignals(True)
        self.ui.part_list.clear()

        all_item = QListWidgetItem("All Parts")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.ui.part_list.addItem(all_item)

        active_parts = sorted({question.part for question in self.viewmodel.active_questions})
        for part in active_parts:
            count = sum(
                1 for question in self.viewmodel.active_questions if question.part == part
            )
            item = QListWidgetItem(f"Part {part} ({count})")
            item.setData(Qt.ItemDataRole.UserRole, part)
            self.ui.part_list.addItem(item)

        self.ui.part_list.setCurrentRow(0)
        self._current_test_part = None
        self.ui.part_list.blockSignals(False)

    def _on_part_selection_changed(self, current, previous):
        if current is None:
            self._current_test_part = None
        else:
            value = current.data(Qt.ItemDataRole.UserRole)
            self._current_test_part = cast(Optional[int], value)
        if self.ui.stacked_widget.currentWidget() == self.test_page:
            self._render_test_questions()

    def _render_test_questions(self):
        clear_layout(self.ui.test_questions_layout)
        self._answer_groups = {}
        self._question_widgets = {}

        filtered_questions = [
            question
            for question in self.viewmodel.active_questions
            if self._current_test_part is None or question.part == self._current_test_part
        ]

        context_order: list[str] = []
        questions_by_context: dict[str, list[object]] = {}
        for question in filtered_questions:
            if question.context_id not in questions_by_context:
                questions_by_context[question.context_id] = []
                context_order.append(question.context_id)
            questions_by_context[question.context_id].append(question)

        for context_id in context_order:
            ctx = self._context_map.get(context_id)
            context_questions = questions_by_context[context_id]
            self.ui.test_questions_layout.addWidget(
                self._context_question_section(ctx, context_questions)
            )

        self.ui.test_questions_layout.addStretch(1)

    def _context_question_section(self, ctx, questions):
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #dadce0; "
            "border-radius: 6px; }"
        )
        layout = QVBoxLayout(section)
        layout.setSpacing(8)

        if ctx is not None:
            context_section = ExamContextSection(
                ctx=ctx,
                title_text=self._context_title(ctx, questions),
                content_html=context_content_html(ctx),
                on_play=self._play_context,
                on_select_audio=self._ignore_context_action,
                on_edit=self._ignore_context_action,
                on_tags=self._show_context_tag_menu,
                tag_names=self.viewmodel.list_question_tags_for_context(ctx.id),
                on_anchor=self._on_context_anchor_clicked,
                on_add_vocabulary=self._add_vocabulary,
                show_select_audio=False,
                show_edit=False,
                parent=section,
            )
            layout.addWidget(context_section)
        else:
            title = QLabel(self._context_title(ctx, questions))
            title.setWordWrap(True)
            title.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #1a73e8; padding: 0 2px;"
            )
            layout.addWidget(title)

        for question in questions:
            layout.addWidget(self._question_card(question, show_context=False))

        return section

    def _question_card(self, question, show_context=True):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e8eaed; "
            "border-radius: 6px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        header = QLabel(f"Question {question.question_number}")
        header.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(header)

        if show_context and question.context_text:
            context = QLabel(question.context_text)
            context.setTextFormat(Qt.TextFormat.PlainText)
            context.setWordWrap(True)
            context.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            context.setStyleSheet(
                "QLabel { border: 1px solid #dadce0; border-radius: 6px; "
                "background-color: #fffde7; padding: 10px; color: #202124; "
                "font-size: 13px; line-height: 1.5; }"
            )
            layout.addWidget(context)

        stem = OptionVocabularyTextBrowser(
            lambda word, context_id=question.context_id: self._add_vocabulary(
                word, context_id
            ),
            card,
        )
        stem.document().setDocumentMargin(0)
        stem.setHtml(html.escape(question.content).replace("\n", "<br>"))
        stem.setStyleSheet("""
            QTextBrowser {
                border: none;
                background: transparent;
                font-size: 13px;
                color: #202124;
            }
        """)
        layout.addWidget(stem)

        group = QButtonGroup(card)
        group.setExclusive(True)
        for option in question.options:
            row = QWidget(card)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            radio = QRadioButton()
            radio.setProperty("display_index", option.display_index)
            radio.setChecked(question.user_choice == option.canonical_letter)
            radio.toggled.connect(
                lambda checked, qid=question.question_id, idx=option.display_index: (
                    self.viewmodel.submit_answer(qid, idx) if checked else None
                )
            )
            group.addButton(radio, option.display_index)
            row_layout.addWidget(radio, 0, Qt.AlignmentFlag.AlignTop)

            option_label = OptionVocabularyTextBrowser(
                lambda word, context_id=question.context_id: self._add_vocabulary(
                    word, context_id
                ),
                row,
            )
            option_label.document().setDocumentMargin(0)
            option_label.setPlainText(f"{option.display_letter}.  {option.text}")
            option_label.setStyleSheet("""
                QTextBrowser {
                    border: none;
                    background: transparent;
                    font-size: 12px;
                    color: #3c4043;
                }
            """)
            row_layout.addWidget(option_label, 1)
            layout.addWidget(row)
        self._answer_groups[question.question_id] = group
        self._question_widgets[question.question_number] = card

        if self.viewmodel.mode == "practice":
            skip_btn = QPushButton("Skip")
            skip_btn.setIcon(qta.icon("fa5s.forward", color="#5f6368"))
            skip_btn.clicked.connect(
                lambda checked=False, qid=question.question_id, g=group: (
                    self._skip_question(qid, g)
                )
            )
            layout.addWidget(skip_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        return card

    def _context_title(self, ctx: Optional[ExamContext], questions: list[ExamQuestion]) -> str:
        first_question = questions[0] if questions else None
        part = getattr(ctx, "part", None) or getattr(first_question, "part", 1)
        if not questions:
            return f"Part {part}"
        question_numbers = [str(question.question_number) for question in questions]
        if len(question_numbers) == 1:
            question_label = f"Question {question_numbers[0]}"
        else:
            question_label = f"Questions {question_numbers[0]}-{question_numbers[-1]}"
        if ctx is None:
            return f"Part {part} | {question_label}"
        type_label = str(ctx.context_type or "Context").replace("_", " ").title()
        return f"Part {part} | Context {ctx.index} | {question_label} | {type_label}"

    def _play_context(self, ctx):
        audio_start, audio_end = context_audio_range(ctx)
        if audio_end <= 0.0:
            return
        if not self.viewmodel.exam or not self.viewmodel.exam.audio_name:
            QMessageBox.warning(self, "Audio", "This exam has no audio file.")
            return

        path = get_local_media_path(self.viewmodel.exam.audio_name)
        if not path.exists():
            QMessageBox.warning(self, "Audio", f"Audio file not found:\n{path}")
            return

        self.play_until = int(audio_end * 1000)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.setPosition(int(audio_start * 1000))
        self.player.play()

    def _ignore_context_action(self, ctx):
        _ = ctx

    def _on_context_anchor_clicked(self, url):
        q_num_str = url.toString() if isinstance(url, QUrl) else str(url)
        try:
            question_number = int(q_num_str)
        except ValueError:
            return

        target = self._question_widgets.get(question_number)
        if target is not None:
            self.ui.test_scroll.ensureWidgetVisible(target)

    def _add_vocabulary(self, word: str, context_id: str) -> None:
        try:
            vocabulary = self.viewmodel.add_vocabulary(word, context_id)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error Saving Vocabulary", f"Could not save vocabulary:\n{exc}"
            )
            return

        QMessageBox.information(
            self,
            "Vocabulary Saved",
            f'Added "{vocabulary.word}" to your vocabulary.',
        )

    def _on_audio_position_changed(self, pos_ms):
        if self.play_until is None:
            return
        if pos_ms >= self.play_until:
            self.player.pause()
            self.play_until = None

    def _show_context_tag_menu(self, ctx: ExamContext, button: QPushButton) -> None:
        popup = TagMenuDialog(ctx, self, viewmodel=self.viewmodel, context_id=ctx.id)
        global_pos = button.mapToGlobal(button.rect().bottomLeft())
        popup.move(global_pos)
        popup.exec()

    def on_question_tag_changed(self, context_id=None):
        if self.ui.stacked_widget.currentWidget() == self.test_page:
            self._render_test_questions()

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

    def _render_attempt_history(self, attempt_summary: AttemptSummary) -> None:
        analytics = self.viewmodel.load_attempt_analytics(attempt_summary.id)
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
        answer_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #202124;"
        )
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

    def _analytics_kpi_row(self, analytics: AttemptAnalytics):
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
        row.addWidget(
            self._counter_card("Correct", analytics.total_correct, "#e6f4ea", "#28a745")
        )
        row.addWidget(
            self._counter_card("Wrong", analytics.total_wrong, "#fce8e6", "#dc3545")
        )
        row.addWidget(
            self._counter_card(
                "Skipped", analytics.total_unanswered, "#f1f3f4", "#6c757d"
            )
        )
        return row

    def _kpi_card(self, title: str, lines: list[str], background: str) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"QFrame {{ background: {background}; border-radius: 6px; }}"
        )
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(label)
        for line in lines:
            item = QLabel(line)
            item.setStyleSheet("color: #3c4043;")
            layout.addWidget(item)
        return card

    def _counter_card(self, title: str, value: int, background: str, color: str):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"QFrame {{ background: {background}; border-radius: 6px; }}"
        )
        layout = QVBoxLayout(card)
        value_label = QLabel(str(value))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {color};"
        )
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
            [
                "Question Category",
                "Correct",
                "Wrong",
                "Skipped",
                "Accuracy %",
                "Questions",
            ]
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

    def _question_badges(self, answers: list[AttemptAnswerDetail]):
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
            badge.setFixedSize(30, 24)
            badge.setStyleSheet(self._answer_badge_style(answer))
            badge.setToolTip(self._answer_badge_tooltip(answer))
            badge.clicked.connect(
                lambda checked=False, item=answer: self._show_answer_dialog(item)
            )
            list_widget.setItemWidget(item, badge)

        return list_widget

    def _badge_list_height(self, answer_count: int) -> int:
        if answer_count <= 0:
            return 34
        rows = ((answer_count - 1) // 8) + 1
        return rows * 32 + 6

    def _answer_badge_text(self, answer: AttemptAnswerDetail) -> str:
        tags = ", ".join(answer.context_tags) if answer.context_tags else "Untagged"
        if len(tags) > 24:
            tags = f"{tags[:21]}..."
        return f"Q{answer.question_number} | {tags}"

    def _answer_badge_tooltip(self, answer: AttemptAnswerDetail) -> str:
        tags = ", ".join(answer.context_tags) if answer.context_tags else "Untagged"
        return f"Question {answer.question_number}\nTags: {tags}"

    def _table_content_height(self, table):
        header_height = table.horizontalHeader().height()
        rows_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        frame_height = table.frameWidth() * 2
        return header_height + rows_height + frame_height + 4

    def _answer_sheet(self, answers: list[AttemptAnswerDetail]):
        sheet = QWidget()
        grid = QGridLayout(sheet)
        grid.setSpacing(8)
        columns = 3
        for index, answer in enumerate(answers):
            tile = self._answer_tile(answer)
            grid.addWidget(tile, index // columns, index % columns)
        return sheet

    def _answer_tile(self, answer: AttemptAnswerDetail):
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
        details_btn.clicked.connect(
            lambda checked=False, item=answer: self._show_answer_dialog(item)
        )
        layout.addWidget(details_btn)
        return tile

    def _show_answer_dialog(self, answer: AttemptAnswerDetail) -> None:
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

        note = QLabel(
            f"Context note:\n{(answer.context_note or '').strip() or 'No context note.'}"
        )
        note.setWordWrap(True)
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        note.setStyleSheet(
            "QLabel { border: 1px solid #dadce0; border-radius: 6px; "
            "background-color: #f8f9fa; padding: 10px; color: #3c4043; }"
        )
        layout.addWidget(note)

        question = QLabel(f"Q{answer.question_number}. {answer.content}")
        question.setWordWrap(True)
        question.setStyleSheet("font-weight: bold; color: #202124;")
        layout.addWidget(question)

        question_note_text = (answer.question_note or "").strip()
        if question_note_text:
            question_note = QLabel(f"Question note:\n{question_note_text}")
            question_note.setWordWrap(True)
            question_note.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            question_note.setStyleSheet(
                "QLabel { border: 1px solid #dadce0; border-radius: 6px; "
                "background-color: #eef7ff; padding: 10px; color: #174ea6; }"
            )
            layout.addWidget(question_note)

        user_choice = answer.user_choice or "not answered"
        details = QLabel(
            f"Your answer: {user_choice} {answer.user_text}\n"
            f"Correct answer: {answer.correct_answer} {answer.correct_text}"
        )
        details.setWordWrap(True)
        layout.addWidget(details)

        footer = QHBoxLayout()
        tag_btn = QPushButton("Tag / Untag")
        tag_btn.setIcon(qta.icon("fa5s.tags", color="#1a73e8"))
        tag_btn.clicked.connect(
            lambda checked=False, item=answer, button=tag_btn, parent=dialog: (
                self._show_answer_tag_menu(item, button, parent)
            )
        )
        footer.addWidget(tag_btn)
        footer.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)
        dialog.exec()
        if self._current_analytics is not None:
            self._render_attempt_history(self._current_analytics.summary)

    def _show_answer_tag_menu(self, answer: AttemptAnswerDetail, button: QPushButton, parent: QWidget) -> None:
        ctx = self._context_for_answer(answer)
        if ctx is None:
            QMessageBox.warning(self, "Tags", "Context not found for this question.")
            return

        popup = TagMenuDialog(ctx, parent, viewmodel=self.viewmodel, context_id=ctx.id)
        global_pos = button.mapToGlobal(button.rect().bottomLeft())
        popup.move(global_pos)
        popup.exec()
        answer.context_tags = self.viewmodel.list_question_tags_for_context(ctx.id)

    def _context_for_answer(self, answer: AttemptAnswerDetail) -> Optional[ExamContext]:
        for ctx in self.viewmodel.contexts:
            if ctx.id == answer.context_id:
                return ctx
        return None

    def _retake_wrong_answers(self, analytics: AttemptAnalytics) -> None:
        wrong_ids = [
            answer.question_id for answer in analytics.answers if not answer.is_correct
        ]
        if not wrong_ids:
            QMessageBox.information(
                self, "Retake", "There are no wrong or skipped answers to retake."
            )
            return
        self.viewmodel.start_review_questions(wrong_ids)

    def _result_card(self, question: AttemptAnswerDetail) -> QWidget:
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
            check.property("part") for check in self._part_checks if check.isChecked()
        ]
        selected_tags = [
            check.property("tag") for check in self._tag_checks if check.isChecked()
        ]
        self.viewmodel.start_test("practice", selected_parts, selected_tags)

    def _skip_question(self, question_id: str, group: QButtonGroup) -> None:
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
            self.ui.timer_label.setText(
                f"Elapsed {self._format_seconds(self.viewmodel.elapsed_seconds())}"
            )
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
        if self.ui.stacked_widget.currentWidget() in (
            self.history_page,
            self.result_page,
            self.dictation_page,
        ):
            if self._dictation_view is not None:
                self._dictation_view.stop()
            self._render_overview()
            return
        self.go_back_callback()

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Exam", message)

    def _format_seconds(self, seconds: float) -> str:
        minutes, secs = divmod(max(0, int(seconds)), 60)
        return f"{minutes:02d}:{secs:02d}"

    def _format_hms(self, seconds: float) -> str:
        hours, remainder = divmod(max(0, int(seconds)), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"

    def _answer_badge_style(self, answer: AttemptAnswerDetail) -> str:
        if answer.is_correct:
            return (
                "QPushButton { background-color: #28a745; color: white; "
                "border: none; border-radius: 4px; font-weight: bold; "
                "font-size: 11px; padding: 4px; text-align: left; }"
            )
        if answer.is_unanswered:
            return (
                "QPushButton { background-color: #f8f9fa; color: #6c757d; "
                "border: 1px solid #6c757d; border-radius: 4px; font-weight: bold; "
                "font-size: 11px; padding: 4px; text-align: left; }"
            )
        return (
            "QPushButton { background-color: #dc3545; color: white; "
            "border: none; border-radius: 4px; font-weight: bold; "
            "font-size: 11px; padding: 4px; text-align: left; }"
        )

    def _primary_button_style(self):
        return (
            "QPushButton { background-color: #1a73e8; color: white; "
            "font-weight: bold; border-radius: 4px; padding: 7px 14px; }"
            "QPushButton:hover { background-color: #1558b0; }"
        )
