# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_context_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTextEdit,
    QVBoxLayout,
)


class Ui_EditContextDialog(object):
    def setupUi(self, EditContextDialog):
        if not EditContextDialog.objectName():
            EditContextDialog.setObjectName(u"EditContextDialog")
        EditContextDialog.resize(640, 420)
        EditContextDialog.setStyleSheet(u"QDialog { background-color: #f8f9fa; }\n"
"QLabel { font-size: 12px; color: #3c4043; }\n"
"QTextEdit {\n"
"    border: 1px solid #dadce0; border-radius: 6px;\n"
"    padding: 6px 8px; font-size: 12px; background-color: white;\n"
"}\n"
"QTextEdit:focus { border-color: #1a73e8; }\n"
"QPushButton#save_btn {\n"
"    background-color: #1a73e8; color: white; font-weight: bold;\n"
"    border-radius: 6px; padding: 8px 20px; font-size: 12px;\n"
"}\n"
"QPushButton#save_btn:hover { background-color: #1558b0; }\n"
"QPushButton#cancel_btn {\n"
"    background-color: white; color: #3c4043;\n"
"    border: 1px solid #dadce0; border-radius: 6px;\n"
"    padding: 8px 20px; font-size: 12px;\n"
"}\n"
"QPushButton#cancel_btn:hover { background-color: #f1f3f4; }")
        self.main_layout = QVBoxLayout(EditContextDialog)
        self.main_layout.setSpacing(12)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.header_label = QLabel(EditContextDialog)
        self.header_label.setObjectName(u"header_label")
        self.header_label.setStyleSheet(u"font-size: 15px; font-weight: bold; color: #202124;")

        self.main_layout.addWidget(self.header_label)

        self.description_label = QLabel(EditContextDialog)
        self.description_label.setObjectName(u"description_label")

        self.main_layout.addWidget(self.description_label)

        self.content_edit = QTextEdit(EditContextDialog)
        self.content_edit.setObjectName(u"content_edit")

        self.main_layout.addWidget(self.content_edit)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.button_spacer)

        self.cancel_btn = QPushButton(EditContextDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(EditContextDialog)
        self.save_btn.setObjectName(u"save_btn")

        self.button_layout.addWidget(self.save_btn)


        self.main_layout.addLayout(self.button_layout)


        self.retranslateUi(EditContextDialog)

        QMetaObject.connectSlotsByName(EditContextDialog)
    # setupUi

    def retranslateUi(self, EditContextDialog):
        EditContextDialog.setWindowTitle(QCoreApplication.translate("EditContextDialog", u"Edit Context", None))
        self.header_label.setText(QCoreApplication.translate("EditContextDialog", u"Editing Context", None))
        self.description_label.setText(QCoreApplication.translate("EditContextDialog", u"Content (text field for READING_PASSAGE; raw JSON for other types):", None))
        self.content_edit.setPlaceholderText(QCoreApplication.translate("EditContextDialog", u"Context content...", None))
        self.cancel_btn.setText(QCoreApplication.translate("EditContextDialog", u"Cancel", None))
        self.save_btn.setText(QCoreApplication.translate("EditContextDialog", u"Save", None))
    # retranslateUi

