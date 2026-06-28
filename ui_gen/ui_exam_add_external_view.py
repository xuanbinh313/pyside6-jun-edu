# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_add_external_view.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTextEdit,
    QVBoxLayout,
)


class Ui_ExamAddExternalView(object):
    def setupUi(self, ExamAddExternalView):
        if not ExamAddExternalView.objectName():
            ExamAddExternalView.setObjectName(u"ExamAddExternalView")
        ExamAddExternalView.resize(800, 600)
        self.main_layout = QVBoxLayout(ExamAddExternalView)
        self.main_layout.setObjectName(u"main_layout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.back_btn = QPushButton(ExamAddExternalView)
        self.back_btn.setObjectName(u"back_btn")
        self.back_btn.setMinimumSize(QSize(80, 0))
        self.back_btn.setMaximumSize(QSize(80, 16777215))

        self.header_layout.addWidget(self.back_btn)

        self.title_label = QLabel(ExamAddExternalView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 20px; font-weight: bold; color: #1a73e8;")

        self.header_layout.addWidget(self.title_label)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)

        self.reset_btn = QPushButton(ExamAddExternalView)
        self.reset_btn.setObjectName(u"reset_btn")

        self.header_layout.addWidget(self.reset_btn)


        self.main_layout.addLayout(self.header_layout)

        self.file_layout = QHBoxLayout()
        self.file_layout.setObjectName(u"file_layout")
        self.file_label = QLabel(ExamAddExternalView)
        self.file_label.setObjectName(u"file_label")

        self.file_layout.addWidget(self.file_label)

        self.pick_btn = QPushButton(ExamAddExternalView)
        self.pick_btn.setObjectName(u"pick_btn")

        self.file_layout.addWidget(self.pick_btn)


        self.main_layout.addLayout(self.file_layout)

        self.text_edit = QTextEdit(ExamAddExternalView)
        self.text_edit.setObjectName(u"text_edit")

        self.main_layout.addWidget(self.text_edit)

        self.action_btn = QPushButton(ExamAddExternalView)
        self.action_btn.setObjectName(u"action_btn")
        self.action_btn.setStyleSheet(u"background-color: #1a73e8; color: white; padding: 15px; font-size: 16px; font-weight: bold;")

        self.main_layout.addWidget(self.action_btn)

        self.progress_label = QLabel(ExamAddExternalView)
        self.progress_label.setObjectName(u"progress_label")
        self.progress_label.setStyleSheet(u"color: #666; font-style: italic;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.progress_label)


        self.retranslateUi(ExamAddExternalView)

        QMetaObject.connectSlotsByName(ExamAddExternalView)
    # setupUi

    def retranslateUi(self, ExamAddExternalView):
        ExamAddExternalView.setWindowTitle(QCoreApplication.translate("ExamAddExternalView", u"Add External Exam", None))
        self.back_btn.setText(QCoreApplication.translate("ExamAddExternalView", u"Back", None))
        self.title_label.setText(QCoreApplication.translate("ExamAddExternalView", u"Add External Exam", None))
        self.reset_btn.setText(QCoreApplication.translate("ExamAddExternalView", u"Reset", None))
        self.file_label.setText(QCoreApplication.translate("ExamAddExternalView", u"No audio selected", None))
        self.pick_btn.setText(QCoreApplication.translate("ExamAddExternalView", u"Select MP3", None))
        self.text_edit.setPlaceholderText(QCoreApplication.translate("ExamAddExternalView", u"Extracted text will appear here...", None))
        self.action_btn.setText(QCoreApplication.translate("ExamAddExternalView", u"Analyze", None))
        self.progress_label.setText("")
    # retranslateUi

