import html
import json
import os
import re

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import src.models.exam as exam_model
from src.models.database import get_session
from src.utils.helpers import get_audio_meta
from src.utils.qt import clear_layout
from src.views.components.add_exam_question_dialog import AddExamQuestionDialog
from src.views.components.import_questions_dialog import ImportQuestionsDialog
from src.views.components.option_question_item import OptionQuestionItem
from ui_gen.ui_exam_groups_widget import Ui_ExamGroupsWidget


# ─────────────────────────────────────────────────────────────────────────────
# ExamGroupsWidget — main Groups & Questions tab
# ─────────────────────────────────────────────────────────────────────────────
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
        self._question_widgets = {}  # question_number → OptionQuestionItem (for scroll navigation)

        self._context_widgets = {}
        self.setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────────────────
    # Public: populate from viewmodel
    # ─────────────────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────────────────
    # q_list population helper — groups by ExamContext
    # ─────────────────────────────────────────────────────────────────────────
    def _populate_q_list(self, questions):
        """Fill q_list with selectable ExamContext items and standalone questions."""
        # Gather distinct context IDs in order of first appearance
        seen_ctx_ids: list[str] = []
        for q in questions:
            if q.context_id and q.context_id not in seen_ctx_ids:
                seen_ctx_ids.append(q.context_id)

        # Fetch all referenced contexts in one query
        ctx_map: dict[str, object] = {}
        if seen_ctx_ids:
            session = get_session()
            try:
                rows = (
                    session.query(exam_model.ExamContext)
                    .filter(exam_model.ExamContext.id.in_(seen_ctx_ids))
                    .all()
                )
                for ctx in rows:
                    session.expunge(ctx)
                    ctx_map[ctx.id] = ctx
            finally:
                session.close()
        # 1. Add Standalone question items (questions that have no context_id)
        standalone = [q for q in questions if not q.context_id]
        if standalone:
            if (
                seen_ctx_ids
            ):  # add a separator header only when there are also context groups
                sep_item = QListWidgetItem("── Standalone Questions ──")
                sep_item.setFlags(Qt.ItemFlag.NoItemFlags | Qt.ItemFlag.ItemIsEnabled)
                sep_item.setData(Qt.ItemDataRole.UserRole + 1, "separator")
                font = sep_item.font()
                font.setItalic(True)
                sep_item.setFont(font)
                sep_item.setForeground(Qt.GlobalColor.darkGray)
                self.ui.q_list.addItem(sep_item)

            for q in standalone:
                label = (
                    f"Question {q.question_number}  [Part {q.part}]  {q.content[:60]}…"
                    if len(q.content) > 60
                    else f"Question {q.question_number}  [Part {q.part}]  {q.content}"
                )
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, q)
                item.setData(Qt.ItemDataRole.UserRole + 1, "standalone_question")
                self.ui.q_list.addItem(item)

        # 2. Add Context items
        for ctx_id in seen_ctx_ids:
            ctx = ctx_map.get(ctx_id)
            if ctx:
                min_question = min(
                    [q.question_number for q in questions if q.context_id == ctx_id]
                )
                max_question = max(
                    [q.question_number for q in questions if q.context_id == ctx_id]
                )

                header_text = f"Questions {min_question}-{max_question}"

                item = QListWidgetItem(header_text)
                item.setData(Qt.ItemDataRole.UserRole, ctx)  # store ctx object
                item.setData(Qt.ItemDataRole.UserRole + 1, "context")  # marker
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(Qt.GlobalColor.darkBlue)
                self.ui.q_list.addItem(item)

    # ─────────────────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────────────────
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
            # Play first question in _question_widgets that has audio
            for q_num in sorted(self._question_widgets.keys()):
                opt_w = self._question_widgets[q_num]
                q = opt_w.question
                audio_start, audio_end = get_audio_meta(q)
                if audio_end > 0.0:
                    self._audio_end_ms = int(audio_end * 1000)
                    self.player.setPosition(int(audio_start * 1000))
                    self.player.play()
                    break

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

    # ─────────────────────────────────────────────────────────────────────────
    # Edit / Delete question
    # ─────────────────────────────────────────────────────────────────────────
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

        session = get_session()
        try:
            for it in items:
                kind = it.data(Qt.ItemDataRole.UserRole + 1)
                obj = it.data(Qt.ItemDataRole.UserRole)
                if kind == "context":
                    # Delete questions first
                    session.query(exam_model.ExamQuestion).filter(
                        exam_model.ExamQuestion.context_id == obj.id
                    ).delete(synchronize_session="fetch")
                    # Delete context
                    session.query(exam_model.ExamContext).filter(
                        exam_model.ExamContext.id == obj.id
                    ).delete(synchronize_session="fetch")
                elif kind == "standalone_question":
                    # Delete question
                    session.query(exam_model.ExamQuestion).filter(
                        exam_model.ExamQuestion.id == obj.id
                    ).delete(synchronize_session="fetch")
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self, "Error Deleting", f"Could not delete items:\n{exc}"
            )
            return
        finally:
            session.close()

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
        if not questions_data:
            return

        session = get_session()
        try:
            # ── Step 1: Insert ExamContext rows & build llm_id → real DB uuid map ──
            llm_to_real_id: dict[str, str] = {}
            for ctx_data in contexts_data:
                llm_id = ctx_data.get("llm_id", "")
                new_ctx = exam_model.ExamContext(
                    exam_id=self.viewmodel.exam_id,
                    part=int(ctx_data.get("part", 1)),
                    context_type=ctx_data.get("context_type", "READING_PASSAGE"),
                    content=ctx_data.get("content", {}),
                    index=ctx_data.get("index", 0),
                )
                session.add(new_ctx)
                session.flush()  # populate new_ctx.id without full commit
                if llm_id:
                    llm_to_real_id[llm_id] = new_ctx.id

            # ── Step 2: Insert ExamQuestion rows with resolved context_id ──────────
            for idx, q_data in enumerate(questions_data):
                # Resolve the LLM's temporary context reference to the real DB uuid
                llm_ctx_id = q_data.get("llm_context_id")
                real_ctx_id = llm_to_real_id.get(llm_ctx_id) if llm_ctx_id else None
                if not real_ctx_id:
                    new_ctx = exam_model.ExamContext(
                        exam_id=self.viewmodel.exam_id,
                        part=1,
                        context_type="STANDALONE",
                        content={"text": ""},
                        index=idx,
                    )
                    session.add(new_ctx)
                    session.flush()
                    real_ctx_id = new_ctx.id

                # additional_meta is already a dict from the parser
                additional_meta = q_data.get("additional_meta") or {
                    "audio_start": 0.0,
                    "audio_end": 0.0,
                    "note": "",
                }
                additional_meta.setdefault("note", "")

                new_q = exam_model.ExamQuestion(
                    context_id=real_ctx_id,
                    question_number=int(q_data.get("question_number", idx + 1)),
                    question_type=q_data.get("question_type", "MULTIPLE_CHOICE"),
                    content=q_data["content"],
                    options=q_data["options"],
                    correct_answer=q_data.get("correct_answer", ""),
                    additional_meta=additional_meta,
                )
                session.add(new_q)

            session.commit()
            n_ctx = len(contexts_data)
            n_q = len(questions_data)
            QMessageBox.information(
                self,
                "Import Successful",
                f"Imported {n_ctx} context(s) and {n_q} question(s) successfully!",
            )
            self.viewmodel.load_exam()
            self.populate()

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self,
                "Error Saving Import",
                f"Could not save to database.\nDetails: {exc}",
            )
        finally:
            session.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Context renderers
    # ─────────────────────────────────────────────────────────────────────────
    def _render_reading_passage(self, ctx):
        """
        Parse READING_PASSAGE content and render double-bracket placeholders
        [[131]] → clickable anchor tags, per spec §4.
        Also attaches an edit icon button next to the passage_label.
        """
        # ── Store current context reference for the edit button ──────────────
        self._current_ctx = ctx

        if isinstance(ctx.content, dict):
            raw = ctx.content.get("text", "")
        else:
            raw = str(ctx.content or "")

        def replace_placeholder(m):
            num = m.group(1)
            return (
                f'<a href="{num}" style="text-decoration:none; color:#0078d4;">'
                f"({num}) ________</a>"
            )

        html_content = re.sub(r"\[\[(\d+)\]\]", replace_placeholder, raw)
        html_content = html_content.replace("\n", "<br>")

        self.ui.passage_browser.setHtml(
            f'<div style="font-family: Georgia, serif; font-size:13px; '
            f'line-height:1.8; color:#202124;">{html_content}</div>'
        )
        # self.ui.passage_label.setVisible(True)
        self.ui.passage_browser.setVisible(True)

        # ── Show the edit-context button row ────────────────────────────────
        if not hasattr(self, "_ctx_edit_row") or self._ctx_edit_row is None:
            self._ctx_edit_row = self._create_ctx_edit_row()
        else:
            self._ctx_edit_row.setVisible(True)

    def _render_audio_srt_context(self, ctx):
        """Display AUDIO_SRT context as a readable transcript."""
        try:
            entries = (
                ctx.content
                if isinstance(ctx.content, list)
                else json.loads(ctx.content)
            )
            lines = [
                f"[{e.get('start', 0):.2f}s – {e.get('end', 0):.2f}s]  {e.get('text', '')}"
                for e in entries
            ]
            self.ui.transcript_browser.setText("\n".join(lines))
            self.ui.transcript_label.setVisible(True)
            self.ui.transcript_browser.setVisible(True)
        except Exception as exc:
            self.ui.transcript_browser.setText(f"Error reading audio context: {exc}")
            self.ui.transcript_browser.setVisible(True)

    # ─────────────────────────────────────────────────────────────────────────
    def _render_audio_srt_context(self, ctx):
        """Display AUDIO_SRT context as a readable transcript."""
        try:
            content = ctx.content
            if isinstance(content, str):
                content = json.loads(content)
            if isinstance(content, dict):
                entries = content.get("srt_lines") or []
                if not entries and content.get("text"):
                    self.ui.transcript_browser.setText(content.get("text", ""))
                    self.ui.transcript_label.setVisible(True)
                    self.ui.transcript_browser.setVisible(True)
                    return
            else:
                entries = content or []

            lines = []
            for entry in entries:
                if isinstance(entry, dict):
                    lines.append(
                        f"[{entry.get('start', 0):.2f}s - {entry.get('end', 0):.2f}s]  {entry.get('text', '')}"
                    )
                else:
                    lines.append(str(entry))
            self.ui.transcript_browser.setText("\n".join(lines))
            self.ui.transcript_label.setVisible(True)
            self.ui.transcript_browser.setVisible(True)
        except Exception as exc:
            self.ui.transcript_browser.setText(f"Error reading audio context: {exc}")
            self.ui.transcript_browser.setVisible(True)

    def _render_image_diagram_context(self, ctx):
        """Display IMAGE_DIAGRAM context image and optional description."""
        content = ctx.content if isinstance(ctx.content, dict) else {}
        image_data_url = content.get("image_data_url", "")
        text = content.get("text", "")

        if image_data_url:
            htmlraw = (
                '<div style="font-family: Arial, sans-serif; color:#202124;">'
                f'<img src="{image_data_url}" style="max-width:100%; height:auto; margin-bottom:10px;" />'
            )
            if text:
                htmlraw += (
                    '<div style="font-size:13px; line-height:1.6; color:#3c4043;">'
                    f"{html.escape(text)}"
                    "</div>"
                )
            htmlraw += "</div>"
            self.ui.passage_browser.setHtml(htmlraw)
        else:
            self.ui.passage_browser.setPlainText(text or "No diagram image saved.")
        self.ui.passage_browser.setVisible(True)

    # Context edit row helper
    # ─────────────────────────────────────────────────────────────────────────
    def _create_ctx_edit_row(self) -> QPushButton:
        """Create (once) a small QWidget with an edit icon button and insert it
        into right_outer_layout directly after passage_label."""
        edit_ctx_btn = QPushButton()
        edit_ctx_btn.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        edit_ctx_btn.setToolTip("Edit reading passage")
        edit_ctx_btn.setFixedSize(24, 24)
        edit_ctx_btn.setStyleSheet("""
            QPushButton {
                border: none; background-color: transparent;
            }
            QPushButton:hover {
                background-color: #e8f0fe; border-radius: 12px;
            }
        """)
        edit_ctx_btn.clicked.connect(self._on_edit_context)
        self.ui.title_outer.layout().addWidget(edit_ctx_btn)
        return edit_ctx_btn

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
                        f"📄  {type_label} (idx {ctx.index})  — {preview}…"
                        if preview
                        else f"📄  {type_label} (idx {ctx.index})"
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
                        f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content[:60]}…"
                        if len(updated_q.content) > 60
                        else f"Q{updated_q.question_number}  [Part {updated_q.part}]  {updated_q.content}"
                    )
                    item.setText(label)
                    item.setData(Qt.ItemDataRole.UserRole, updated_q)
                    break

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
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
        session = get_session()
        try:
            numbers = [
                row[0]
                for row in session.query(exam_model.ExamQuestion.question_number)
                .filter(exam_model.ExamQuestion.context_id == ctx.id)
                .order_by(exam_model.ExamQuestion.question_number.asc())
                .all()
            ]
        finally:
            session.close()

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

    def _create_context_section(self, ctx):
        section = QWidget(self.ui.options_container)
        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(self._context_item_label(ctx))
        title.setWordWrap(True)
        title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #1a73e8; padding: 0 2px;"
        )
        header_layout.addWidget(title, 1)

        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon("fa5s.edit", color="#1a73e8"))
        edit_btn.setToolTip("Edit context")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; }
            QPushButton:hover { background-color: #e8f0fe; border-radius: 12px; }
        """)
        edit_btn.clicked.connect(lambda checked=False, c=ctx: self._on_edit_context(c))
        header_layout.addWidget(edit_btn)
        layout.addLayout(header_layout)

        body = QLabel(self._context_content_html(ctx))
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setOpenExternalLinks(False)
        body.setWordWrap(True)
        body.linkActivated.connect(self._on_passage_anchor_clicked)
        body.setStyleSheet("""
            QLabel {
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: #fffde7;
                padding: 10px;
                font-size: 13px;
                color: #202124;
                line-height: 1.6;
            }
        """)
        layout.addWidget(body)
        return section

    def _context_content_html(self, ctx):
        content = ctx.content
        if ctx.context_type == "AUDIO_SRT":
            return self._audio_srt_context_html(content)
        if ctx.context_type == "IMAGE_DIAGRAM":
            return self._image_diagram_context_html(content)

        if isinstance(content, dict):
            raw = str(content.get("text", ""))
        else:
            raw = str(content or "")
        safe = html.escape(raw)

        def replace_placeholder(match):
            num = match.group(1)
            return (
                f'<a href="{num}" style="text-decoration:none; color:#0078d4;">'
                f"({num}) ________</a>"
            )

        safe = re.sub(r"\[\[(\d+)\]\]", replace_placeholder, safe)
        return safe.replace("\n", "<br>") or "<i>No context text saved.</i>"

    def _audio_srt_context_html(self, content):
        try:
            if isinstance(content, str):
                content = json.loads(content)
            if isinstance(content, dict):
                entries = content.get("srt_lines") or []
                if not entries and content.get("text"):
                    return html.escape(str(content.get("text", ""))).replace("\n", "<br>")
            else:
                entries = content or []

            lines = []
            for entry in entries:
                if isinstance(entry, dict):
                    lines.append(
                        f"[{entry.get('start', 0):.2f}s - {entry.get('end', 0):.2f}s] "
                        f"{html.escape(str(entry.get('text', '')))}"
                    )
                else:
                    lines.append(html.escape(str(entry)))
            return "<br>".join(lines) or "<i>No transcript context saved.</i>"
        except Exception as exc:
            return f"<i>Error reading audio context: {html.escape(str(exc))}</i>"

    def _image_diagram_context_html(self, content):
        content = content if isinstance(content, dict) else {}
        image_data_url = content.get("image_data_url", "")
        text = html.escape(str(content.get("text", ""))).replace("\n", "<br>")
        parts = []
        if image_data_url:
            parts.append(
                f'<img src="{image_data_url}" style="max-width:100%; height:auto; margin-bottom:10px;" />'
            )
        parts.append(text or "<i>No diagram image saved.</i>")
        return "<br>".join(parts)

    def _questions_for_context(self, context_id):
        session = get_session()
        try:
            questions = (
                session.query(exam_model.ExamQuestion)
                .filter(exam_model.ExamQuestion.context_id == context_id)
                .order_by(exam_model.ExamQuestion.question_number.asc())
                .all()
            )
            for question in questions:
                session.expunge(question)
            return questions
        finally:
            session.close()

    def _clear_options(self):
        """Remove all OptionQuestionItem children from the scrollable layout."""
        clear_layout(self.ui.options_layout, keep_tail=1)
        self._question_widgets.clear()
        self._context_widgets.clear()

    def populate_tags(self):
        self.ui.tag_filter_list.blockSignals(True)
        checked_tags = set()
        for i in range(self.ui.tag_filter_list.count()):
            item = self.ui.tag_filter_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_tags.add(item.text())

        self.ui.tag_filter_list.clear()

        session = get_session()
        try:
            all_tags_rows = (
                session.query(exam_model.UserQuestionTag.tag_name)
                .filter(exam_model.UserQuestionTag.user_id == "local_user")
                .distinct()
                .all()
            )
            all_tags = sorted([r[0] for r in all_tags_rows])

            for tag_name in all_tags:
                item = QListWidgetItem(tag_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if tag_name in checked_tags:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.ui.tag_filter_list.addItem(item)
        finally:
            session.close()

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

        session = get_session()
        try:
            if not selected_tags:
                contexts = (
                    session.query(exam_model.ExamContext)
                    .filter(exam_model.ExamContext.exam_id == self.viewmodel.exam_id)
                    .order_by(
                        exam_model.ExamContext.part.asc(),
                        exam_model.ExamContext.index.asc(),
                    )
                    .all()
                )
            else:
                contexts = (
                    session.query(exam_model.ExamContext)
                    .join(
                        exam_model.ExamQuestion,
                        exam_model.ExamQuestion.context_id == exam_model.ExamContext.id,
                    )
                    .join(
                        exam_model.UserQuestionTag,
                        exam_model.ExamQuestion.id
                        == exam_model.UserQuestionTag.question_id,
                    )
                    .filter(
                        exam_model.ExamContext.exam_id == self.viewmodel.exam_id,
                        exam_model.UserQuestionTag.user_id == "local_user",
                        exam_model.UserQuestionTag.tag_name.in_(selected_tags),
                    )
                    .distinct()
                    .order_by(
                        exam_model.ExamContext.part.asc(),
                        exam_model.ExamContext.index.asc(),
                    )
                    .all()
                )

            for ctx in contexts:
                session.expunge(ctx)
            self._populate_q_list(contexts)
            self._render_question_page(contexts)
        finally:
            session.close()

        self.ui.q_list.blockSignals(False)
        self.ui.title_label.setText("Question Details")

    def on_question_tag_changed(self):
        self.populate_tags()
        self._on_filter_changed()

    def on_question_audio_changed(self, question):
        context_id = getattr(question, "context_id", None)
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
