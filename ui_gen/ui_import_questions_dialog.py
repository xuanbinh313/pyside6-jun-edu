# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'import_questions_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize)
from PySide6.QtWidgets import (QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTextEdit, QVBoxLayout)

class Ui_ImportQuestionsDialog(object):
    def setupUi(self, ImportQuestionsDialog):
        if not ImportQuestionsDialog.objectName():
            ImportQuestionsDialog.setObjectName(u"ImportQuestionsDialog")
        ImportQuestionsDialog.resize(720, 600)
        self.main_layout = QVBoxLayout(ImportQuestionsDialog)
        self.main_layout.setSpacing(10)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.step1_title = QLabel(ImportQuestionsDialog)
        self.step1_title.setObjectName(u"step1_title")
        self.step1_title.setStyleSheet(u"font-weight: bold; font-size: 14px; color: #1a73e8;")

        self.main_layout.addWidget(self.step1_title)

        self.description_label = QLabel(ImportQuestionsDialog)
        self.description_label.setObjectName(u"description_label")
        self.description_label.setStyleSheet(u"color: #5f6368; font-size: 12px;")
        self.description_label.setWordWrap(True)

        self.main_layout.addWidget(self.description_label)

        self.prompt_edit = QTextEdit(ImportQuestionsDialog)
        self.prompt_edit.setObjectName(u"prompt_edit")
        self.prompt_edit.setMinimumSize(QSize(0, 160))
        self.prompt_edit.setMaximumSize(QSize(16777215, 160))
        self.prompt_edit.setStyleSheet(u"background-color: #f8f9fa; border: 1px solid #dadce0; border-radius: 4px; font-family: monospace; font-size: 11px;")
        self.prompt_edit.setReadOnly(True)

        self.main_layout.addWidget(self.prompt_edit)

        self.copy_btn = QPushButton(ImportQuestionsDialog)
        self.copy_btn.setObjectName(u"copy_btn")
        self.copy_btn.setStyleSheet(u"background-color: #1a73e8; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")

        self.main_layout.addWidget(self.copy_btn)

        self.divider_line = QFrame(ImportQuestionsDialog)
        self.divider_line.setObjectName(u"divider_line")
        self.divider_line.setStyleSheet(u"color: #dadce0;")
        self.divider_line.setFrameShape(QFrame.Shape.HLine)
        self.divider_line.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.divider_line)

        self.step2_title = QLabel(ImportQuestionsDialog)
        self.step2_title.setObjectName(u"step2_title")
        self.step2_title.setStyleSheet(u"font-weight: bold; font-size: 14px; color: #1a73e8;")

        self.main_layout.addWidget(self.step2_title)

        self.json_edit = QTextEdit(ImportQuestionsDialog)
        self.json_edit.setObjectName(u"json_edit")
        self.json_edit.setStyleSheet(u"border: 1px solid #dadce0; border-radius: 4px; font-family: monospace; font-size: 11px;")

        self.main_layout.addWidget(self.json_edit)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.button_spacer)

        self.cancel_btn = QPushButton(ImportQuestionsDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setStyleSheet(u"padding: 6px 12px;")

        self.button_layout.addWidget(self.cancel_btn)

        self.import_btn = QPushButton(ImportQuestionsDialog)
        self.import_btn.setObjectName(u"import_btn")
        self.import_btn.setStyleSheet(u"background-color: #34a853; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")

        self.button_layout.addWidget(self.import_btn)


        self.main_layout.addLayout(self.button_layout)


        self.retranslateUi(ImportQuestionsDialog)

        QMetaObject.connectSlotsByName(ImportQuestionsDialog)
    # setupUi

    def retranslateUi(self, ImportQuestionsDialog):
        ImportQuestionsDialog.setWindowTitle(QCoreApplication.translate("ImportQuestionsDialog", u"Import Questions - LLM JSON Import", None))
        self.step1_title.setText(QCoreApplication.translate("ImportQuestionsDialog", u"Step 1 - Copy prompt, then paste into Gemini/ChatGPT with your exam image", None))
        self.description_label.setText(QCoreApplication.translate("ImportQuestionsDialog", u"The LLM will extract contexts (passages, audio, diagrams) and questions as a structured JSON object, aligned with ExamContext and ExamQuestion models.", None))
        self.copy_btn.setText(QCoreApplication.translate("ImportQuestionsDialog", u"Copy Prompt to Clipboard", None))
        self.step2_title.setText(QCoreApplication.translate("ImportQuestionsDialog", u"Step 2 - Paste the generated JSON data below and click Import", None))
        self.cancel_btn.setText(QCoreApplication.translate("ImportQuestionsDialog", u"Cancel", None))
        self.import_btn.setText(QCoreApplication.translate("ImportQuestionsDialog", u"Import && Save", None))
    # retranslateUi

