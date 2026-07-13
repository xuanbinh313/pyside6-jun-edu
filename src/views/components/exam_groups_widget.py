import html
from typing import Any, Optional, Protocol, TypedDict, Union, cast

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTextBrowser,
    QWidget,
)
from src.models.exam import (
    ContextSchema,
    ExamContext,
    ExamQuestion,
    ExamSrtChunk,
    QuestionSchema,
)
from src.utils.helpers import get_audio_meta, get_local_media_path
from src.utils.qt import clear_layout
from src.viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from src.views.components.add_exam_question_dialog import AddExamQuestionDialog
from src.views.components.exam_context_html import context_content_html
from src.views.components.exam_context_section import (
    ExamContextSection,
    context_audio_meta,
    context_audio_range,
)
from src.views.components.import_questions_agent_dialog import (
    ImportQuestionsAgentDialog,
)
from src.views.components.import_questions_dialog import ImportQuestionsDialog
from src.views.components.option_question_item import OptionQuestionItem
from src.views.components.select_transcript_dialog import SelectTranscriptDialog
from src.views.components.tag_menu_dialog import TagMenuDialog
from ui_gen.ui_exam_groups_widget import Ui_ExamGroupsWidget


class ImportResult(TypedDict):
    context_count: int
    created_count: int
    updated_numbers: list[int]
    duplicate_numbers: list[int]


class ImportDialogResult(Protocol):
    @property
    def result_contexts(self) -> list[ContextSchema]:
        ...

    @property
    def result_questions(self) -> list[QuestionSchema]:
        ...

    @property
    def result_answer_key(self) -> dict[int, str]:
        ...


QuestionWidgetMap = dict[int, OptionQuestionItem]
ContextWidgetMap = dict[str, ExamContextSection]
ContextNoteLabelMap = dict[str, QTextBrowser]
QuestionsByContextMap = dict[str, list[ExamQuestion]]


# ExamGroupsWidget â€” main Groups & Questions tab
class ExamGroupsWidget(QWidget):
    def __init__(self, viewmodel: ExamDetailsViewModel, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.viewmodel: ExamDetailsViewModel = viewmodel

        # Audio Player (for listening questions)
        self.player: QMediaPlayer = QMediaPlayer()
        self.audio_output: QAudioOutput = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.positionChanged.connect(self._on_position_changed)

        self._audio_end_ms: int = 0  # current clip end in ms
        self._question_widgets: QuestionWidgetMap = {}

        self._context_widgets: ContextWidgetMap = {}
        self._context_note_labels: ContextNoteLabelMap = {}
        self._all_contexts: list[ExamContext] = []
        self._active_part: Optional[int] = None
        self._questions_by_context: QuestionsByContextMap = {}
        self._loading_label: Optional[QLabel] = None
        self._current_ctx: Optional[ExamContext] = None
        self._is_loading: bool = False
        self.setup_ui()

    # UI construction
    def setup_ui(self) -> None:
        self.ui: Ui_ExamGroupsWidget = Ui_ExamGroupsWidget()
        self.ui.setupUi(self)

        # Wire up references to widgets inside the loaded UI

        # Setup icons
        self.add_q_btn: QPushButton = QPushButton(self)
        self.add_q_btn.setIcon(qta.icon("fa5s.plus", color="#1a73e8"))
        self.add_q_btn.setToolTip("Add exam question")
        self.add_q_btn.setMinimumSize(28, 28)
        self.add_q_btn.setMaximumSize(28, 28)
        self.ui.q_label_layout.insertWidget(
            self.ui.q_label_layout.count() - 1, self.add_q_btn
        )
        self.import_agent_btn: QPushButton = QPushButton(self)
        self.import_agent_btn.setIcon(qta.icon("fa5s.robot", color="#9334e6"))
        self.import_agent_btn.setToolTip("Import questions with AI agent")
        self.import_agent_btn.setMinimumSize(28, 28)
        self.import_agent_btn.setMaximumSize(28, 28)
        self.ui.q_label_layout.insertWidget(
            self.ui.q_label_layout.count() - 1, self.import_agent_btn
        )
        self.ui.import_q_btn.setIcon(qta.icon("fa5s.file-import", color="#34a853"))
        self.ui.listen_btn.setIcon(qta.icon("fa5s.play", color="white"))
        self._setup_part_tabs()
        self._setup_loading_label()

        # Setup connections
        self.add_q_btn.clicked.connect(self._on_add_question_clicked)
        self.import_agent_btn.clicked.connect(self._on_import_questions_agent_clicked)
        self.ui.import_q_btn.clicked.connect(self._on_import_questions_clicked)
        self.ui.tag_filter_list.itemChanged.connect(self._on_filter_changed)
        self.ui.q_list.currentItemChanged.connect(self._on_question_selected)
        self.ui.listen_btn.clicked.connect(self._on_listen_clicked)
        self.ui.passage_browser.anchorClicked.connect(self._on_passage_anchor_clicked)

        # Allow Ctrl/Shift multi-select so users can bulk-delete
        self.ui.q_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        # Right-click context menu on the question list
        self.ui.q_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.q_list.customContextMenuRequested.connect(self._on_q_list_context_menu)

    def _setup_part_tabs(self) -> None:
        self.part_tabs = QTabBar(self.ui.right_outer)
        self.part_tabs.setExpanding(False)
        self.part_tabs.setDrawBase(False)
        self.part_tabs.setUsesScrollButtons(True)
        self.part_tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 7px 14px;
                margin-right: 4px;
                border: 1px solid #dadce0;
                border-radius: 4px;
                color: #3c4043;
                background: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                color: #1a73e8;
                border-color: #1a73e8;
                background: #e8f0fe;
            }
        """)
        self.ui.title_label.setVisible(False)
        self.ui.title_outer.insertWidget(0, self.part_tabs)
        self.part_tabs.currentChanged.connect(self._on_part_tab_changed)

    def _setup_loading_label(self) -> None:
        label = QLabel("Loading questions...")
        label.setVisible(False)
        label.setStyleSheet(
            "color: #5f6368; padding: 8px 10px; "
            "border: 1px solid #dadce0; border-radius: 4px; background: #f8f9fa;"
        )
        self._loading_label = label
        self.ui.right_outer_layout.insertWidget(1, label)

    def _set_loading(self, is_loading: bool) -> None:
        if self._is_loading == is_loading:
            return
        self._is_loading = is_loading
        if self._loading_label is not None:
            self._loading_label.setVisible(is_loading)
        self.ui.q_list.setEnabled(not is_loading)
        self.part_tabs.setEnabled(not is_loading)
        if is_loading:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    def _populate_part_tabs(self, contexts: list[ExamContext]) -> None:
        parts = sorted({ctx.part for ctx in contexts})
        previous_part = self._active_part

        self.part_tabs.blockSignals(True)
        while self.part_tabs.count() > 0:
            self.part_tabs.removeTab(0)
        for part in parts:
            self.part_tabs.addTab(f"Part {part}")
            self.part_tabs.setTabData(self.part_tabs.count() - 1, part)
        self.part_tabs.blockSignals(False)

        if not parts:
            self._active_part = None
            return

        target_part = previous_part if previous_part in parts else parts[0]
        self._set_active_part(target_part)

    def _set_active_part(self, part: int) -> None:
        self._active_part = part
        for index in range(self.part_tabs.count()):
            tab_part = cast(Optional[int], self.part_tabs.tabData(index))
            if tab_part == part:
                self.part_tabs.blockSignals(True)
                self.part_tabs.setCurrentIndex(index)
                self.part_tabs.blockSignals(False)
                break

    def _on_part_tab_changed(self, index: int) -> None:
        part = cast(object, self.part_tabs.tabData(index))
        if not isinstance(part, int):
            return
        self._active_part = part
        self._set_loading(True)
        try:
            self._render_active_part()
        finally:
            self._set_loading(False)

    def _active_contexts(self) -> list[ExamContext]:
        if self._active_part is None:
            return []
        return [ctx for ctx in self._all_contexts if ctx.part == self._active_part]

    def _render_active_part(self) -> None:
        contexts = self._active_contexts()
        self.ui.q_list.blockSignals(True)
        self.ui.q_list.clear()
        self._questions_by_context.clear()
        self._render_question_page(contexts)
        self._populate_q_list(contexts)
        self.ui.q_list.blockSignals(False)
        if self._active_part is None:
            self.ui.title_label.setText("Question Details")
        else:
            self.ui.title_label.setText(f"Part {self._active_part}")

    # Public: populate from viewmodel
    def populate(self) -> None:
        self._set_loading(True)
        try:
            self.player.stop()
            self.populate_tags()
            self.ui.q_list.clear()
            self._clear_options()
            self.ui.title_label.setText("Question Details")
            self.ui.listen_widget.setVisible(False)
            self.ui.passage_browser.setVisible(False)
            self.ui.transcript_label.setVisible(False)
            self.ui.transcript_browser.setVisible(False)

            # Load audio source
            if self.viewmodel.exam and self.viewmodel.exam.audio_name:
                path = get_local_media_path(self.viewmodel.exam.audio_name)
                if path.exists():
                    self.player.setSource(QUrl.fromLocalFile(str(path)))

            contexts = self.viewmodel.list_contexts()
            self.viewmodel.contexts = contexts
            self._all_contexts = contexts
            self._populate_part_tabs(contexts)
            self._render_active_part()
        finally:
            self._set_loading(False)

    # Slots
    def _on_question_selected(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        _ = previous
        self.player.stop()

        if not current:
            return

        item_kind = cast(Optional[str], current.data(Qt.ItemDataRole.UserRole + 1))
        if item_kind == "separator":
            return

        if item_kind == "context":
            ctx = cast(ExamContext, current.data(Qt.ItemDataRole.UserRole))
            self._current_ctx = ctx
            self.ui.title_label.setText(self._context_item_label(ctx))

            target = self._context_widgets.get(ctx.id)
            if target is not None:
                self.ui.options_scroll.ensureWidgetVisible(target)
            return

        elif item_kind == "standalone_question":
            q = cast(ExamQuestion, current.data(Qt.ItemDataRole.UserRole))
            self._current_ctx = None
            self.ui.title_label.setText(f"Question {q.question_number}")
            target = self._question_widgets.get(q.question_number)
            if target is not None:
                self.ui.options_scroll.ensureWidgetVisible(target)
            return

    def _on_listen_clicked(self) -> None:
        current = self.ui.q_list.currentItem()
        if not current:
            return
        item_kind = cast(Optional[str], current.data(Qt.ItemDataRole.UserRole + 1))
        if item_kind == "standalone_question":
            q = cast(ExamQuestion, current.data(Qt.ItemDataRole.UserRole))
            audio_start, audio_end = cast(tuple[float, float], get_audio_meta(q))
            if audio_end > 0.0:
                self._audio_end_ms = int(audio_end * 1000)
                self.player.setPosition(int(audio_start * 1000))
                self.player.play()
        elif item_kind == "context":
            ctx = cast(ExamContext, current.data(Qt.ItemDataRole.UserRole))
            self._play_context_audio(ctx)

    def _on_position_changed(self, pos_ms: int) -> None:
        """Pause automatically when the clip end is reached."""
        if (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            and self._audio_end_ms > 0
            and pos_ms >= self._audio_end_ms
        ):
            self.player.pause()

    def _on_passage_anchor_clicked(self, url: Union[QUrl, str]) -> None:
        """
        Called when the user clicks [[N]] anchor in the reading passage.
        Scrolls the matching OptionQuestionItem into view, or shows an inline QMenu.
        """
        q_num_str = url.toString() if isinstance(url, QUrl) else url
        try:
            q_num = int(q_num_str)
        except ValueError:
            return

        target = self._question_widgets.get(q_num)
        if target:
            self.ui.options_scroll.ensureWidgetVisible(target)
        else:
            # Show a quick informational popup at cursor
            menu = QMenu(self)
            menu.addAction(f"Question {q_num} not in current view")
            menu.exec(QCursor.pos())

    # Edit / Delete question
    def _on_q_list_context_menu(self, pos: QPoint) -> None:
        """Show Edit / Delete context menu for the right-clicked list item."""
        clicked_item = self.ui.q_list.itemAt(pos)
        if not clicked_item:
            return

        item_kind = cast(Optional[str], clicked_item.data(Qt.ItemDataRole.UserRole + 1))
        if item_kind == "separator":
            return
        if item_kind != "context":
            return

        selected_items: list[QListWidgetItem] = [
            it
            for it in self.ui.q_list.selectedItems()
            if it.data(Qt.ItemDataRole.UserRole + 1) == "context"
        ]
        if clicked_item not in selected_items:
            self.ui.q_list.clearSelection()
            clicked_item.setSelected(True)
            selected_items = [clicked_item]

        n = len(selected_items)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #dadce0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
                font-size: 12px;
                color: #202124;
            }
            QMenu::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
                border-radius: 4px;
            }
            QMenu::separator { height: 1px; background: #dadce0; margin: 4px 8px; }
        """)

        edit_action: Optional[QAction] = None
        if n == 1:
            if item_kind == "context":
                edit_action = menu.addAction(
                    qta.icon("fa5s.edit", color="#1a73e8"), "Edit Context"
                )
            menu.addSeparator()

        delete_label = f"Delete {n} Items" if n > 1 else "Delete Item"
        delete_action = menu.addAction(
            qta.icon("fa5s.trash-alt", color="#ea4335"), delete_label
        )

        action = cast(
            Optional[QAction],
            menu.exec(self.ui.q_list.viewport().mapToGlobal(pos)),
        )

        if edit_action and action == edit_action:
            if item_kind == "context":
                self._on_edit_context(
                    cast(ExamContext, clicked_item.data(Qt.ItemDataRole.UserRole))
                )
        elif action == delete_action:
            self._on_delete_items(selected_items)

    def _legacy_question_edit_removed(self, item: QListWidgetItem) -> None:
        """Open EditQuestionDialog for the given list item."""
        _ = item.data(Qt.ItemDataRole.UserRole)
        return

    def _on_delete_items(self, items: list[QListWidgetItem]) -> None:
        """Confirm and delete selected contexts or standalone questions.
        Deleting a context also deletes all associated questions.
        """
        n = len(items)
        if n == 0:
            return

        context_names: list[str] = []
        standalone_nums: list[str] = []
        for it in items:
            kind = cast(Optional[str], it.data(Qt.ItemDataRole.UserRole + 1))
            obj = it.data(Qt.ItemDataRole.UserRole)
            if kind == "context":
                ctx = cast(ExamContext, obj)
                type_label = ctx.context_type.replace("_", " ").title()
                context_names.append(f"{type_label} (idx {ctx.index})")
            elif kind == "standalone_question":
                q = cast(ExamQuestion, obj)
                standalone_nums.append(f"Q{q.question_number}")

        msg_parts: list[str] = []
        if context_names:
            msg_parts.append(
                "Contexts to delete (and all their questions):\n- "
                + "\n- ".join(context_names)
            )
        if standalone_nums:
            msg_parts.append(
                "Standalone questions to delete:\n- " + "\n- ".join(standalone_nums)
            )

        msg = (
            "\n\n".join(msg_parts)
            + "\n\nAre you sure you want to delete these? This action cannot be undone."
        )

        reply = QMessageBox.question(
            self,
            "Delete Confirmation",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            context_ids: list[str] = []
            question_ids: list[str] = []
            for it in items:
                kind = cast(Optional[str], it.data(Qt.ItemDataRole.UserRole + 1))
                obj = it.data(Qt.ItemDataRole.UserRole)
                if kind == "context":
                    context_ids.append(cast(ExamContext, obj).id)
                elif kind == "standalone_question":
                    question_ids.append(cast(ExamQuestion, obj).id)
            self.viewmodel.delete_contexts_and_questions(context_ids, question_ids)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error Deleting", f"Could not delete items:\n{exc}"
            )
            return

        # Re-populate / refresh UI
        self._on_filter_changed()

    def _on_add_question_clicked(self) -> None:
        dialog = AddExamQuestionDialog(self.viewmodel.exam_id, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.viewmodel.load_exam()
        self.populate()
        saved_context_id :Optional[str] = cast(Optional[str], dialog.saved_context_id)
        if saved_context_id:
            self._select_context_id(saved_context_id)
        QMessageBox.information(self, "Created", "Question created successfully.")

    def _on_import_questions_clicked(self) -> None:
        dialog = ImportQuestionsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._save_import_result(cast(ImportDialogResult, dialog))

    def _on_import_questions_agent_clicked(self) -> None:
        dialog = ImportQuestionsAgentDialog(self)
        dialog.viewmodel.request_ready.connect(self._save_agent_request_result)
        dialog.exec()

    def _save_import_result(self, dialog: ImportDialogResult) -> None:
        contexts_data: list[ContextSchema] = dialog.result_contexts
        questions_data: list[QuestionSchema] = dialog.result_questions
        answer_key: dict[int, str] = dialog.result_answer_key
        self._save_import_payload(
            contexts_data,
            questions_data,
            answer_key,
            show_success_message=True,
            error_title="Error Saving Import",
        )

    def _save_agent_request_result(self, task_id: str, result: dict) -> None:
        contexts_data = cast(
            list[ContextSchema], result.get("contexts", []) or []
        )
        questions_data = cast(
            list[QuestionSchema], result.get("questions", []) or []
        )
        raw_answer_key = result.get("answer_key", {}) or {}
        answer_key: dict[int, str] = {
            int(key): str(value) for key, value in raw_answer_key.items()
        }
        saved = self._save_import_payload(
            contexts_data,
            questions_data,
            answer_key,
            show_success_message=False,
            error_title="Error Saving Agent Import",
        )
        if saved:
            print(f"Saved agent request {task_id} to database.")

    def _save_import_payload(
        self,
        contexts_data: list[ContextSchema],
        questions_data: list[QuestionSchema],
        answer_key: dict[int, str],
        *,
        show_success_message: bool,
        error_title: str,
    ) -> bool:
        if not questions_data and not answer_key:
            return False

        try:
            answer_updated_numbers = self.viewmodel.update_correct_answers(answer_key)
            result: ImportResult = {
                "context_count": 0,
                "created_count": 0,
                "updated_numbers": [],
                "duplicate_numbers": [],
            }
            if questions_data:
                result = cast(
                    ImportResult,
                    self.viewmodel.import_contexts_and_questions(
                        contexts_data, questions_data
                    ),
                )
                duplicate_numbers = result["duplicate_numbers"]
                if duplicate_numbers:
                    duplicate_text = ", ".join(
                        f"Q{number}" for number in duplicate_numbers
                    )
                    QMessageBox.warning(
                        self,
                        "Duplicate Question Numbers",
                        f"The import data contains duplicate question number(s): {duplicate_text}.\n"
                        "Please keep each question number unique in the import JSON.",
                    )
                    return False

            n_ctx = result["context_count"]
            created_count = result["created_count"]
            updated_numbers = result["updated_numbers"]
            updated_text = ""
            if updated_numbers:
                duplicate_text = ", ".join(f"Q{number}" for number in updated_numbers)
                updated_text = (
                    f"\nUpdated existing duplicate number(s): {duplicate_text}."
                )
            if show_success_message:
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Imported {n_ctx} context(s).\n"
                    f"Created {created_count} question(s), updated {len(updated_numbers)} question(s)."
                    f"\nUpdated {len(answer_updated_numbers)} existing answer key(s)."
                    f"{updated_text}",
                )
            self.viewmodel.load_exam()
            self.populate()
            return True

        except Exception as exc:
            QMessageBox.critical(
                self,
                error_title,
                f"Could not save to database.\nDetails: {exc}",
            )
            return False

    def _on_edit_context(self, ctx: Optional[ExamContext] = None) -> None:
        if ctx is None:
            ctx = self._current_ctx
        if not ctx:
            return
        dialog = AddExamQuestionDialog(self.viewmodel.exam_id, context=ctx, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated_ctx = dialog.context
        if updated_ctx is None:
            return
        self._apply_context_update(updated_ctx)
        self._select_visible_context_item(updated_ctx.id)

    def _replace_context_in_collection(
        self, contexts: list[ExamContext], updated_ctx: ExamContext
    ) -> None:
        for index, context in enumerate(contexts):
            if context.id == updated_ctx.id:
                contexts[index] = updated_ctx
                return

    def _apply_context_update(self, updated_ctx: ExamContext) -> None:
        self._replace_context_in_collection(self._all_contexts, updated_ctx)
        self._replace_context_in_collection(self.viewmodel.contexts, updated_ctx)
        if self._current_ctx and self._current_ctx.id == updated_ctx.id:
            self._current_ctx = updated_ctx

        self._refresh_ctx_header_item(updated_ctx)

        section = self._context_widgets.get(updated_ctx.id)
        if section is not None:
            section.update_context(
                updated_ctx,
                self._context_item_label(updated_ctx),
                context_content_html(updated_ctx),
                self.viewmodel.list_question_tags_for_context(updated_ctx.id),
            )

    def _select_visible_context_item(self, context_id: str) -> None:
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            ctx = cast(Optional[ExamContext], item.data(Qt.ItemDataRole.UserRole))
            if (
                item.data(Qt.ItemDataRole.UserRole + 1) == "context"
                and ctx
                and ctx.id == context_id
            ):
                self.ui.q_list.setCurrentItem(item)
                return

    def _refresh_ctx_header_item(self, ctx: ExamContext) -> None:
        """Find and update the q_list header item for the given context."""
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == "context":
                stored = cast(Optional[ExamContext], item.data(Qt.ItemDataRole.UserRole))
                if stored and stored.id == ctx.id:
                    item.setText(self._context_item_label(ctx))
                    item.setData(Qt.ItemDataRole.UserRole, ctx)
                    break

    def on_question_edited(self, updated_q: ExamQuestion) -> None:
        """Called by OptionQuestionItem after an inline question edit to refresh the list item or current view."""
        # Update standalone question if matches
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == "standalone_question":
                q = cast(Optional[ExamQuestion], item.data(Qt.ItemDataRole.UserRole))
                if q and q.id == updated_q.id:
                    label = (
                        f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content[:60]}â€¦"
                        if len(updated_q.content) > 60
                        else f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content}"
                    )
                    item.setText(label)
                    item.setData(Qt.ItemDataRole.UserRole, updated_q)
                    break

    def on_question_checked(self, question: ExamQuestion) -> None:
        scroll_position = self._options_scroll_position()
        context_id = getattr(question, "context_id", None)
        if not context_id:
            return

        label = self._context_note_labels.get(context_id)
        if label is None:
            return

        note = self._context_note_text(question)
        if not note:
            label.clear()
            label.setVisible(False)
            self._restore_options_scroll_position(scroll_position)
            return

        safe_note = html.escape(note).replace("\n", "<br>")
        label.setHtml(safe_note)
        label.setVisible(True)
        self._restore_options_scroll_position(scroll_position)

    def _context_note_text(self, question: ExamQuestion) -> str:
        ctx = cast(Optional[ExamContext], getattr(question, "context", None))
        note = self._note_from_context(ctx)
        if note:
            return note

        context_id = getattr(question, "context_id", None)
        if not context_id:
            return ""

        for context in getattr(self.viewmodel, "contexts", []):
            if context.id == context_id:
                return self._note_from_context(context)
        return ""

    def _note_from_context(self, ctx: Optional[ExamContext]) -> str:
        meta = cast(dict[str, Any], context_audio_meta(ctx))
        note = meta.get("note", "")
        return str(note).strip()

    def _populate_q_list(self, contexts: list[ExamContext]) -> None:
        """Fill q_list with contexts and questions for the selected part."""
        for ctx in sorted(contexts, key=lambda c: (c.part or 0, c.index or 0)):
            item = QListWidgetItem(self._context_item_label(ctx))
            item.setData(Qt.ItemDataRole.UserRole, ctx)
            item.setData(Qt.ItemDataRole.UserRole + 1, "context")
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(Qt.GlobalColor.darkBlue)
            self.ui.q_list.addItem(item)

    def _context_item_label(self, ctx: ExamContext) -> str:
        numbers = self.viewmodel.context_question_numbers(ctx.id)

        type_label = ctx.context_type.replace("_", " ").title()
        if not numbers:
            return f"{type_label} (idx {ctx.index})"
        if len(numbers) == 1:
            return f"Question {numbers[0]} - {type_label}"
        return f"Questions {numbers[0]}-{numbers[-1]} - {type_label}"

    def _render_question_page(self, contexts: list[ExamContext]) -> None:
        """Render all visible contexts and questions into one scrollable page."""
        self._clear_options()
        self.ui.passage_browser.setVisible(False)
        self.ui.transcript_label.setVisible(False)
        self.ui.transcript_browser.setVisible(False)
        self.ui.listen_widget.setVisible(False)

        sorted_contexts = sorted(contexts, key=lambda c: (c.part or 0, c.index or 0))
        for ctx in sorted_contexts:
            section = self._create_context_section(ctx)
            self._context_widgets[ctx.id] = section
            self._insert_scroll_widget(section)

            questions = self._questions_for_context(ctx.id)
            self._questions_by_context[ctx.id] = questions
            for question in questions:
                opt_w = OptionQuestionItem(
                    question,
                    exam_id=self.viewmodel.exam_id,
                    on_add_vocabulary=self._add_vocabulary,
                )
                self._question_widgets[question.question_number] = opt_w
                self._insert_scroll_widget(opt_w)

        if not sorted_contexts:
            empty_label = QLabel("No questions match the selected tags.")
            empty_label.setStyleSheet("color: #5f6368; padding: 12px;")
            self._insert_scroll_widget(empty_label)

    def _insert_scroll_widget(self, widget: QWidget) -> None:
        count = self.ui.options_layout.count()
        self.ui.options_layout.insertWidget(max(0, count - 1), widget)

    def _options_scroll_position(self) -> int:
        return self.ui.options_scroll.verticalScrollBar().value()

    def _restore_options_scroll_position(self, position: int) -> None:
        QApplication.processEvents()
        scroll_bar = self.ui.options_scroll.verticalScrollBar()
        scroll_bar.setValue(min(position, scroll_bar.maximum()))

    def _play_context_audio(self, ctx: ExamContext) -> None:
        if not ctx:
            return
        audio_start, audio_end = context_audio_range(ctx)
        if audio_end <= 0.0:
            return
        self._audio_end_ms = int(audio_end * 1000)
        self.player.setPosition(int(audio_start * 1000))
        self.player.play()

    def _on_select_context_audio_segment(self, ctx: ExamContext) -> None:
        if not ctx:
            return
        exam_id = self.viewmodel.exam_id
        if not exam_id:
            QMessageBox.warning(self, "No Exam", "Could not determine the exam.")
            return

        dialog = SelectTranscriptDialog(exam_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_chunks:
            return

        selected_chunks = cast(list[ExamSrtChunk], dialog.selected_chunks)
        first = selected_chunks[0]
        last = selected_chunks[-1]
        try:
            updated_ctx = self.viewmodel.update_context_audio_segment(
                ctx.id, float(first.start_time), float(last.end_time)
            )
            if not updated_ctx:
                QMessageBox.warning(self, "Missing Context", "Context not found.")
                return

            ctx.additional_meta = updated_ctx.additional_meta
            context_id = ctx.id
        except Exception as exc:
            QMessageBox.critical(
                self, "Error Saving", f"Could not save segment to context:\n{exc}"
            )
            return

        self._reload_and_select_context(context_id)

    def _create_context_section(self, ctx: ExamContext) -> ExamContextSection:
        section = ExamContextSection(
            ctx=ctx,
            title_text=self._context_item_label(ctx),
            content_html=context_content_html(ctx),
            on_play=self._play_context_audio,
            on_select_audio=self._on_select_context_audio_segment,
            on_edit=self._on_edit_context,
            on_tags=self._show_context_tag_menu,
            tag_names=self.viewmodel.list_question_tags_for_context(ctx.id),
            on_anchor=self._on_passage_anchor_clicked,
            on_add_vocabulary=self._add_vocabulary,
            parent=self.ui.options_container,
        )
        self._context_note_labels[ctx.id] = section.note_label
        return section

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

    def _show_context_tag_menu(self, ctx: ExamContext, button: QPushButton) -> None:
        popup = TagMenuDialog(ctx, self, viewmodel=self.viewmodel, context_id=ctx.id)
        popup.move(button.mapToGlobal(QPoint(0, button.height())))
        popup.exec()
        # self.on_question_tag_changed()

    def _questions_for_context(self, context_id: str) -> list[ExamQuestion]:
        return self.viewmodel.list_questions_for_context(context_id)

    def _clear_options(self) -> None:
        """Remove all OptionQuestionItem children from the scrollable layout."""
        clear_layout(self.ui.options_layout, keep_tail=1)
        self._question_widgets.clear()
        self._context_widgets.clear()
        self._context_note_labels.clear()
        self._questions_by_context.clear()

    def populate_tags(self) -> None:
        self.ui.tag_filter_list.blockSignals(True)
        self.ui.tag_filter_list.setStyleSheet("""
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        checked_tags: set[str] = set()
        for i in range(self.ui.tag_filter_list.count()):
            item = self.ui.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_tags.add(item.text())

        self.ui.tag_filter_list.clear()

        for tag_name in self.viewmodel.list_question_tags():
            item = QListWidgetItem(tag_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if tag_name in checked_tags:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.ui.tag_filter_list.addItem(item)

        self.ui.tag_filter_list.blockSignals(False)

    def _on_filter_changed(self) -> None:
        selected_tags: list[str] = []
        for i in range(self.ui.tag_filter_list.count()):
            item = self.ui.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tags.append(item.text())
        contexts = self.viewmodel.list_contexts(selected_tags)
        self.viewmodel.contexts = contexts
        self._all_contexts = contexts
        self._populate_part_tabs(contexts)
        self._render_active_part()

    def on_question_tag_changed(self, context_id: Optional[str] = None) -> None:
        self.populate_tags()
        if not context_id:
            return

        tag_names = self.viewmodel.list_question_tags_for_context(context_id)
        section = self._context_widgets.get(context_id)
        if section is not None:
            section.update_tags(tag_names)

    def on_question_audio_changed(self, question: ExamQuestion) -> None:
        context_id = question.context_id
        self._reload_and_select_context(context_id)

    def _reload_and_select_context(self, context_id: Optional[str]) -> None:
        self.viewmodel.load_exam()
        self.populate()
        if not context_id:
            return
        self._select_context_id(context_id)

    def _select_context_id(self, context_id: Optional[str]) -> None:
        if not context_id:
            return
        for context in self._all_contexts:
            if context.id == context_id:
                self._set_active_part(context.part)
                self._render_active_part()
                break
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            ctx = cast(Optional[ExamContext], item.data(Qt.ItemDataRole.UserRole))
            if (
                item.data(Qt.ItemDataRole.UserRole + 1) == "context"
                and ctx
                and ctx.id == context_id
            ):
                self.ui.q_list.setCurrentItem(item)
                break

    def closeEvent(self, event: QCloseEvent) -> None:
        self.player.stop()
        super().closeEvent(event)
