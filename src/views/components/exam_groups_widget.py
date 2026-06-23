import html
import os

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from src.utils.helpers import get_audio_meta
from src.utils.qt import clear_layout
from src.views.components.add_exam_question_dialog import AddExamQuestionDialog
from src.views.components.exam_context_html import context_content_html
from src.views.components.exam_context_section import (
    ExamContextSection,
    context_audio_range,
)
from src.views.components.import_questions_dialog import ImportQuestionsDialog
from src.views.components.option_question_item import OptionQuestionItem
from src.views.components.select_transcript_dialog import SelectTranscriptDialog
from ui_gen.ui_exam_groups_widget import Ui_ExamGroupsWidget


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ExamGroupsWidget â€” main Groups & Questions tab
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExamGroupsWidget(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel

        # Audio Player (for listening questions)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.positionChanged.connect(self._on_position_changed)

        self._audio_end_ms = 0  # current clip end in ms
        self._question_widgets = {}  # question_number â†’ OptionQuestionItem (for scroll navigation)

        self._context_widgets = {}
        self._context_note_labels = {}
        self.setup_ui()

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # UI construction
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def setup_ui(self):
        self.ui = Ui_ExamGroupsWidget()
        self.ui.setupUi(self)

        # Wire up references to widgets inside the loaded UI

        # Setup icons
        self.add_q_btn = QPushButton(self)
        self.add_q_btn.setIcon(qta.icon("fa5s.plus", color="#1a73e8"))
        self.add_q_btn.setToolTip("Add exam question")
        self.add_q_btn.setMinimumSize(28, 28)
        self.add_q_btn.setMaximumSize(28, 28)
        self.ui.q_label_layout.insertWidget(
            self.ui.q_label_layout.count() - 1, self.add_q_btn
        )
        self.ui.import_q_btn.setIcon(qta.icon("fa5s.file-import", color="#34a853"))
        self.ui.listen_btn.setIcon(qta.icon("fa5s.play", color="white"))

        # Setup connections
        self.add_q_btn.clicked.connect(self._on_add_question_clicked)
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

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Public: populate from viewmodel
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def populate(self):
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
        if self.viewmodel.exam and self.viewmodel.exam.full_audio_url:
            path = self.viewmodel.exam.full_audio_url
            if os.path.exists(path):
                self.player.setSource(QUrl.fromLocalFile(path))
            elif path.startswith("http"):
                self.player.setSource(QUrl(path))

        contexts = getattr(self.viewmodel, "contexts", [])
        self._populate_q_list(contexts)
        self._render_question_page(contexts)

    # Slots
    def _on_question_selected(self, current, previous):
        self.player.stop()

        if not current:
            return

        item_kind = current.data(Qt.ItemDataRole.UserRole + 1)
        if item_kind == "separator":
            return

        if item_kind == "context":
            ctx = current.data(Qt.ItemDataRole.UserRole)
            self._current_ctx = ctx
            self.ui.title_label.setText(self._context_item_label(ctx))

            target = self._context_widgets.get(ctx.id)
            if target is not None:
                self.ui.options_scroll.ensureWidgetVisible(target)
            return

        elif item_kind == "standalone_question":
            q = current.data(Qt.ItemDataRole.UserRole)
            self._current_ctx = None
            self.ui.title_label.setText(f"Question {q.question_number}")
            target = self._question_widgets.get(q.question_number)
            if target is not None:
                self.ui.options_scroll.ensureWidgetVisible(target)
            return

    def _on_listen_clicked(self):
        current = self.ui.q_list.currentItem()
        if not current:
            return
        item_kind = current.data(Qt.ItemDataRole.UserRole + 1)
        if item_kind == "standalone_question":
            q = current.data(Qt.ItemDataRole.UserRole)
            audio_start, audio_end = get_audio_meta(q)
            if audio_end > 0.0:
                self._audio_end_ms = int(audio_end * 1000)
                self.player.setPosition(int(audio_start * 1000))
                self.player.play()
        elif item_kind == "context":
            ctx = current.data(Qt.ItemDataRole.UserRole)
            self._play_context_audio(ctx)

    def _on_position_changed(self, pos_ms):
        """Pause automatically when the clip end is reached."""
        if (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            and self._audio_end_ms > 0
            and pos_ms >= self._audio_end_ms
        ):
            self.player.pause()

    def _on_passage_anchor_clicked(self, url):
        """
        Called when the user clicks [[N]] anchor in the reading passage.
        Scrolls the matching OptionQuestionItem into view, or shows an inline QMenu.
        """
        q_num_str = url.toString() if hasattr(url, "toString") else str(url)
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
    def _on_q_list_context_menu(self, pos: QPoint):
        """Show Edit / Delete context menu for the right-clicked list item."""
        clicked_item = self.ui.q_list.itemAt(pos)
        if not clicked_item:
            return

        item_kind = clicked_item.data(Qt.ItemDataRole.UserRole + 1)
        if item_kind == "separator":
            return

        selected_items = [
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

        edit_action = None
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

        action = menu.exec(self.ui.q_list.viewport().mapToGlobal(pos))

        if edit_action and action == edit_action:
            if item_kind == "context":
                self._on_edit_context(clicked_item.data(Qt.ItemDataRole.UserRole))
        elif action == delete_action:
            self._on_delete_items(selected_items)

    def _legacy_question_edit_removed(self, item: QListWidgetItem):
        """Open EditQuestionDialog for the given list item."""
        item.data(Qt.ItemDataRole.UserRole)
        return

    def _on_delete_items(self, items: list):
        """Confirm and delete selected contexts or standalone questions.
        Deleting a context also deletes all associated questions.
        """
        n = len(items)
        if n == 0:
            return

        context_names = []
        standalone_nums = []
        for it in items:
            kind = it.data(Qt.ItemDataRole.UserRole + 1)
            obj = it.data(Qt.ItemDataRole.UserRole)
            if kind == "context":
                type_label = obj.context_type.replace("_", " ").title()
                context_names.append(f"{type_label} (idx {obj.index})")
            elif kind == "standalone_question":
                standalone_nums.append(f"Q{obj.question_number}")

        msg_parts = []
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
            context_ids = []
            question_ids = []
            for it in items:
                kind = it.data(Qt.ItemDataRole.UserRole + 1)
                obj = it.data(Qt.ItemDataRole.UserRole)
                if kind == "context":
                    context_ids.append(obj.id)
                elif kind == "standalone_question":
                    question_ids.append(obj.id)
            self.viewmodel.delete_contexts_and_questions(context_ids, question_ids)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error Deleting", f"Could not delete items:\n{exc}"
            )
            return

        # Re-populate / refresh UI
        self._on_filter_changed()

    def _on_add_question_clicked(self):
        dialog = AddExamQuestionDialog(self.viewmodel.exam_id, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.viewmodel.load_exam()
        self.populate()
        saved_context_id = dialog.saved_context_id
        if saved_context_id:
            for i in range(self.ui.q_list.count()):
                item = self.ui.q_list.item(i)
                kind = item.data(Qt.ItemDataRole.UserRole + 1)
                obj = item.data(Qt.ItemDataRole.UserRole)
                if kind == "context" and obj and obj.id == saved_context_id:
                    self.ui.q_list.setCurrentItem(item)
                    break
        QMessageBox.information(self, "Created", "Question created successfully.")

    def _on_import_questions_clicked(self):
        dialog = ImportQuestionsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        contexts_data = dialog.result_contexts  # list[dict] with 'llm_id' key
        questions_data = dialog.result_questions  # list[dict] with 'llm_context_id' key
        answer_key = getattr(dialog, "result_answer_key", {})
        if not questions_data and not answer_key:
            return

        try:
            answer_updated_numbers = self.viewmodel.update_correct_answers(answer_key)
            result = {
                "context_count": 0,
                "created_count": 0,
                "updated_numbers": [],
                "duplicate_numbers": [],
            }
            if questions_data:
                result = self.viewmodel.import_contexts_and_questions(
                    contexts_data, questions_data
                )
                duplicate_numbers = result.get("duplicate_numbers", [])
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
                    return

            n_ctx = result.get("context_count", 0)
            created_count = result.get("created_count", 0)
            updated_numbers = result.get("updated_numbers", [])
            updated_text = ""
            if updated_numbers:
                duplicate_text = ", ".join(f"Q{number}" for number in updated_numbers)
                updated_text = (
                    f"\nUpdated existing duplicate number(s): {duplicate_text}."
                )
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

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error Saving Import",
                f"Could not save to database.\nDetails: {exc}",
            )

    def _on_edit_context(self, ctx=None):
        ctx = ctx or getattr(self, "_current_ctx", None)
        if not ctx:
            return
        dialog = AddExamQuestionDialog(self.viewmodel.exam_id, context=ctx, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.viewmodel.load_exam()
        self.populate()
        saved_context_id = dialog.saved_context_id
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            stored = item.data(Qt.ItemDataRole.UserRole)
            if (
                item.data(Qt.ItemDataRole.UserRole + 1) == "context"
                and stored
                and stored.id == saved_context_id
            ):
                self.ui.q_list.setCurrentItem(item)
                break

    def _refresh_ctx_header_item(self, ctx):
        """Find and update the q_list header item for the given context."""
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == "context":
                stored = item.data(Qt.ItemDataRole.UserRole)
                if stored and stored.id == ctx.id:
                    type_label = ctx.context_type.replace("_", " ").title()
                    preview = ""
                    if isinstance(ctx.content, dict):
                        preview = ctx.content.get("text", "")[:60]
                    else:
                        preview = str(ctx.content or "")[:60]
                    header_text = (
                        f"ðŸ“„  {type_label} (idx {ctx.index})  â€” {preview}â€¦"
                        if preview
                        else f"ðŸ“„  {type_label} (idx {ctx.index})"
                    )
                    item.setText(header_text)
                    item.setData(Qt.ItemDataRole.UserRole, ctx)
                    break

    def on_question_edited(self, updated_q):
        """Called by OptionQuestionItem after an inline question edit to refresh the list item or current view."""
        # Update standalone question if matches
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole + 1) == "standalone_question":
                q = item.data(Qt.ItemDataRole.UserRole)
                if q and q.id == updated_q.id:
                    label = (
                        f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content[:60]}â€¦"
                        if len(updated_q.content) > 60
                        else f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content}"
                    )
                    item.setText(label)
                    item.setData(Qt.ItemDataRole.UserRole, updated_q)
                    break

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Helpers
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def on_question_checked(self, question):
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
            return

        safe_note = html.escape(note).replace("\n", "<br>")
        label.setText(f"<b>Note:</b> {safe_note}")
        label.setVisible(True)
        self.ui.options_scroll.ensureWidgetVisible(label)

    def _context_note_text(self, question):
        ctx = getattr(question, "context", None)
        meta = (
            ctx.additional_meta if ctx and isinstance(ctx.additional_meta, dict) else {}
        )
        note = str(meta.get("note", "")).strip()
        if note:
            return note

        context_id = getattr(question, "context_id", None)
        if not context_id:
            return ""

        for context in getattr(self.viewmodel, "contexts", []):
            if context.id == context_id and isinstance(context.additional_meta, dict):
                return str(context.additional_meta.get("note", "")).strip()
        return ""

    def _populate_q_list(self, contexts):
        """Fill q_list with all ExamContext rows, grouped under Part headers."""
        current_part = None
        for ctx in sorted(contexts, key=lambda c: (c.part or 0, c.index or 0)):
            if ctx.part != current_part:
                current_part = ctx.part
                part_item = QListWidgetItem(f"Part {current_part}")
                part_item.setFlags(Qt.ItemFlag.NoItemFlags | Qt.ItemFlag.ItemIsEnabled)
                part_item.setData(Qt.ItemDataRole.UserRole + 1, "separator")
                font = part_item.font()
                font.setBold(True)
                part_item.setFont(font)
                part_item.setForeground(Qt.GlobalColor.darkGray)
                self.ui.q_list.addItem(part_item)

            item = QListWidgetItem(self._context_item_label(ctx))
            item.setData(Qt.ItemDataRole.UserRole, ctx)
            item.setData(Qt.ItemDataRole.UserRole + 1, "context")
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(Qt.GlobalColor.darkBlue)
            self.ui.q_list.addItem(item)

    def _context_item_label(self, ctx):
        numbers = self.viewmodel.context_question_numbers(ctx.id)

        type_label = ctx.context_type.replace("_", " ").title()
        if not numbers:
            return f"{type_label} (idx {ctx.index})"
        if len(numbers) == 1:
            return f"Question {numbers[0]} - {type_label}"
        return f"Questions {numbers[0]}-{numbers[-1]} - {type_label}"

    def _render_question_page(self, contexts):
        """Render all visible contexts and questions into one scrollable page."""
        self._clear_options()
        self.ui.passage_browser.setVisible(False)
        self.ui.transcript_label.setVisible(False)
        self.ui.transcript_browser.setVisible(False)
        self.ui.listen_widget.setVisible(False)

        current_part = None
        sorted_contexts = sorted(contexts, key=lambda c: (c.part or 0, c.index or 0))
        for ctx in sorted_contexts:
            if ctx.part != current_part:
                current_part = ctx.part
                part_label = QLabel(f"Part {current_part}")
                part_label.setStyleSheet(
                    "font-size: 15px; font-weight: bold; color: #5f6368; "
                    "padding: 8px 2px 2px 2px;"
                )
                self._insert_scroll_widget(part_label)

            section = self._create_context_section(ctx)
            self._context_widgets[ctx.id] = section
            self._insert_scroll_widget(section)

            questions = self._questions_for_context(ctx.id)
            for question in questions:
                opt_w = OptionQuestionItem(question, exam_id=self.viewmodel.exam_id)
                self._question_widgets[question.question_number] = opt_w
                self._insert_scroll_widget(opt_w)

        if not sorted_contexts:
            empty_label = QLabel("No questions match the selected tags.")
            empty_label.setStyleSheet("color: #5f6368; padding: 12px;")
            self._insert_scroll_widget(empty_label)

    def _insert_scroll_widget(self, widget):
        count = self.ui.options_layout.count()
        self.ui.options_layout.insertWidget(max(0, count - 1), widget)

    def _play_context_audio(self, ctx):
        if not ctx:
            return
        audio_start, audio_end = context_audio_range(ctx)
        if audio_end <= 0.0:
            return
        self._audio_end_ms = int(audio_end * 1000)
        self.player.setPosition(int(audio_start * 1000))
        self.player.play()

    def _on_select_context_audio_segment(self, ctx):
        if not ctx:
            return
        exam_id = self.viewmodel.exam_id
        if not exam_id:
            QMessageBox.warning(self, "No Exam", "Could not determine the exam.")
            return

        dialog = SelectTranscriptDialog(exam_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_chunks:
            return

        first = dialog.selected_chunks[0]
        last = dialog.selected_chunks[-1]
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

    def _create_context_section(self, ctx):
        section = ExamContextSection(
            ctx=ctx,
            title_text=self._context_item_label(ctx),
            content_html=context_content_html(ctx),
            on_play=self._play_context_audio,
            on_select_audio=self._on_select_context_audio_segment,
            on_edit=self._on_edit_context,
            on_anchor=self._on_passage_anchor_clicked,
            parent=self.ui.options_container,
        )
        self._context_note_labels[ctx.id] = section.note_label
        return section

    def _questions_for_context(self, context_id):
        return self.viewmodel.list_questions_for_context(context_id)

    def _clear_options(self):
        """Remove all OptionQuestionItem children from the scrollable layout."""
        clear_layout(self.ui.options_layout, keep_tail=1)
        self._question_widgets.clear()
        self._context_widgets.clear()
        self._context_note_labels.clear()

    def populate_tags(self):
        self.ui.tag_filter_list.blockSignals(True)
        checked_tags = set()
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

    def _on_filter_changed(self):
        selected_tags = []
        for i in range(self.ui.tag_filter_list.count()):
            item = self.ui.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tags.append(item.text())

        self.ui.q_list.blockSignals(True)
        self.ui.q_list.clear()
        self._clear_options()

        contexts = self.viewmodel.list_contexts(selected_tags)
        self._populate_q_list(contexts)
        self._render_question_page(contexts)

        self.ui.q_list.blockSignals(False)
        self.ui.title_label.setText("Question Details")

    def on_question_tag_changed(self):
        self.populate_tags()
        self._on_filter_changed()

    def on_question_audio_changed(self, question):
        context_id = getattr(question, "context_id", None)
        self._reload_and_select_context(context_id)

    def _reload_and_select_context(self, context_id):
        self.viewmodel.load_exam()
        self.populate()
        if not context_id:
            return
        for i in range(self.ui.q_list.count()):
            item = self.ui.q_list.item(i)
            ctx = item.data(Qt.ItemDataRole.UserRole)
            if (
                item.data(Qt.ItemDataRole.UserRole + 1) == "context"
                and ctx
                and ctx.id == context_id
            ):
                self.ui.q_list.setCurrentItem(item)
                break

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)
