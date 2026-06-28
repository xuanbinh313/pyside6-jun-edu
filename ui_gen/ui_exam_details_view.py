# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_details_view.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QVBoxLayout,
)


class Ui_ExamDetailsView(object):
    def setupUi(self, ExamDetailsView):
        if not ExamDetailsView.objectName():
            ExamDetailsView.setObjectName(u"ExamDetailsView")
        ExamDetailsView.resize(900, 650)
        self.main_layout = QVBoxLayout(ExamDetailsView)
        self.main_layout.setObjectName(u"main_layout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.back_btn = QPushButton(ExamDetailsView)
        self.back_btn.setObjectName(u"back_btn")
        self.back_btn.setMinimumSize(QSize(80, 0))
        self.back_btn.setMaximumSize(QSize(80, 16777215))

        self.header_layout.addWidget(self.back_btn)

        self.title_label = QLabel(ExamDetailsView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 20px; font-weight: bold; color: #1a73e8;")

        self.header_layout.addWidget(self.title_label)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)


        self.main_layout.addLayout(self.header_layout)

        self.tabs = QTabWidget(ExamDetailsView)
        self.tabs.setObjectName(u"tabs")
        self.tabs.setStyleSheet(u"QTabBar::tab { padding: 10px 20px; font-weight: bold; }\n"
"QTabBar::tab:selected { background-color: #1a73e8; color: white; border-radius: 4px; }")

        self.main_layout.addWidget(self.tabs)


        self.retranslateUi(ExamDetailsView)

        QMetaObject.connectSlotsByName(ExamDetailsView)
    # setupUi

    def retranslateUi(self, ExamDetailsView):
        ExamDetailsView.setWindowTitle(QCoreApplication.translate("ExamDetailsView", u"Exam Management", None))
        self.back_btn.setText(QCoreApplication.translate("ExamDetailsView", u"Back", None))
        self.title_label.setText(QCoreApplication.translate("ExamDetailsView", u"Exam Management", None))
    # retranslateUi

