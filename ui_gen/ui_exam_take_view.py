# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_take_view.ui'
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class Ui_ExamTakeView(object):
    def setupUi(self, ExamTakeView: QWidget):
        if not ExamTakeView.objectName():
            ExamTakeView.setObjectName(u"ExamTakeView")
        ExamTakeView.resize(980, 700)
        self.main_layout = QVBoxLayout(ExamTakeView)
        self.main_layout.setObjectName(u"main_layout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.back_btn = QPushButton(ExamTakeView)
        self.back_btn.setObjectName(u"back_btn")
        self.back_btn.setMinimumSize(QSize(80, 0))
        self.back_btn.setMaximumSize(QSize(80, 16777215))

        self.header_layout.addWidget(self.back_btn)

        self.title_layout = QVBoxLayout()
        self.title_layout.setObjectName(u"title_layout")
        self.title_label = QLabel(ExamTakeView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 22px; font-weight: bold; color: #1a73e8;")

        self.title_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(ExamTakeView)
        self.subtitle_label.setObjectName(u"subtitle_label")
        self.subtitle_label.setStyleSheet(u"color: #5f6368;")

        self.title_layout.addWidget(self.subtitle_label)


        self.header_layout.addLayout(self.title_layout)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)

        self.timer_label = QLabel(ExamTakeView)
        self.timer_label.setObjectName(u"timer_label")
        self.timer_label.setStyleSheet(u"font-size: 14px; font-weight: bold; color: #3c4043;")

        self.header_layout.addWidget(self.timer_label)


        self.main_layout.addLayout(self.header_layout)

        self.stacked_widget = QStackedWidget(ExamTakeView)
        self.stacked_widget.setObjectName(u"stacked_widget")

        self.main_layout.addWidget(self.stacked_widget)


        self.retranslateUi(ExamTakeView)

        QMetaObject.connectSlotsByName(ExamTakeView)
    # setupUi

    def retranslateUi(self, ExamTakeView: QWidget):
        ExamTakeView.setWindowTitle(QCoreApplication.translate("ExamTakeView", u"Exam", None))
        self.back_btn.setText(QCoreApplication.translate("ExamTakeView", u"Back", None))
        self.title_label.setText(QCoreApplication.translate("ExamTakeView", u"Exam", None))
        self.subtitle_label.setText("")
        self.timer_label.setText(QCoreApplication.translate("ExamTakeView", u"00:00", None))
    # retranslateUi

