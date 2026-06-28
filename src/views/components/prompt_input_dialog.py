from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextEdit, QVBoxLayout


class PromptInputDialog(QDialog):
    def __init__(self, prompt: str, parent=None, title: str = "Edit Prompt"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(title, self)
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #202124;")
        layout.addWidget(header)

        self.prompt_edit = QTextEdit(self)
        self.prompt_edit.setPlainText(prompt)
        self.prompt_edit.setStyleSheet(
            "border: 1px solid #dadce0; border-radius: 4px; "
            "font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.prompt_edit, 1)

        self.button_box = QDialogButtonBox(self)
        self.save_btn = self.button_box.addButton(
            "Save", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.cancel_btn = self.button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self.button_box)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def prompt_text(self) -> str:
        return self.prompt_edit.toPlainText()
