# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'select_transcript_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)


class Ui_SelectTranscriptDialog(object):
    def setupUi(self, SelectTranscriptDialog):
        if not SelectTranscriptDialog.objectName():
            SelectTranscriptDialog.setObjectName(u"SelectTranscriptDialog")
        SelectTranscriptDialog.resize(600, 400)
        self.main_layout = QVBoxLayout(SelectTranscriptDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.description_label = QLabel(SelectTranscriptDialog)
        self.description_label.setObjectName(u"description_label")
        self.description_label.setStyleSheet(u"font-size: 13px; color: #5f6368;")

        self.main_layout.addWidget(self.description_label)

        self.list_widget = QListWidget(SelectTranscriptDialog)
        self.list_widget.setObjectName(u"list_widget")
        self.list_widget.setStyleSheet(u"QListWidget {\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 6px;\n"
"    background-color: white;\n"
"    padding: 5px;\n"
"}\n"
"QListWidget::item {\n"
"    padding: 8px;\n"
"    border-bottom: 1px solid #f1f3f4;\n"
"}\n"
"QListWidget::item:selected {\n"
"    background-color: #e8f0fe;\n"
"    color: #1a73e8;\n"
"}")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.main_layout.addWidget(self.list_widget)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.button_spacer)

        self.cancel_btn = QPushButton(SelectTranscriptDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setStyleSheet(u"QPushButton {\n"
"    padding: 6px 12px;\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 4px;\n"
"    background-color: white;\n"
"}\n"
"QPushButton:hover { background-color: #f1f3f4; }")

        self.button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton(SelectTranscriptDialog)
        self.ok_btn.setObjectName(u"ok_btn")
        self.ok_btn.setStyleSheet(u"QPushButton {\n"
"    padding: 6px 16px;\n"
"    background-color: #1a73e8;\n"
"    color: white;\n"
"    font-weight: bold;\n"
"    border-radius: 4px;\n"
"}\n"
"QPushButton:hover { background-color: #1558b0; }")

        self.button_layout.addWidget(self.ok_btn)


        self.main_layout.addLayout(self.button_layout)


        self.retranslateUi(SelectTranscriptDialog)

        QMetaObject.connectSlotsByName(SelectTranscriptDialog)
    # setupUi

    def retranslateUi(self, SelectTranscriptDialog):
        SelectTranscriptDialog.setWindowTitle(QCoreApplication.translate("SelectTranscriptDialog", u"Select Transcript Segment", None))
        self.description_label.setText(QCoreApplication.translate("SelectTranscriptDialog", u"Select one or more transcript lines to set the audio segment:", None))
        self.cancel_btn.setText(QCoreApplication.translate("SelectTranscriptDialog", u"Cancel", None))
        self.ok_btn.setText(QCoreApplication.translate("SelectTranscriptDialog", u"Save Segment", None))
    # retranslateUi

