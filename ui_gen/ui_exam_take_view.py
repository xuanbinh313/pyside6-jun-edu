# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_take_view.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSplitter, QStackedWidget, QVBoxLayout,
    QWidget)

class Ui_ExamTakeView(object):
    def setupUi(self, ExamTakeView):
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
        self.overview_page = QWidget()
        self.overview_page.setObjectName(u"overview_page")
        self.overview_layout = QVBoxLayout(self.overview_page)
        self.overview_layout.setObjectName(u"overview_layout")
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.addWidget(self.overview_page)
        self.test_page = QWidget()
        self.test_page.setObjectName(u"test_page")
        self.test_layout = QVBoxLayout(self.test_page)
        self.test_layout.setObjectName(u"test_layout")
        self.test_layout.setContentsMargins(0, 0, 0, 0)
        self.test_splitter = QSplitter(self.test_page)
        self.test_splitter.setObjectName(u"test_splitter")
        self.test_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.part_panel = QWidget(self.test_splitter)
        self.part_panel.setObjectName(u"part_panel")
        self.part_panel.setMinimumSize(QSize(150, 0))
        self.part_panel.setMaximumSize(QSize(220, 16777215))
        self.part_panel_layout = QVBoxLayout(self.part_panel)
        self.part_panel_layout.setObjectName(u"part_panel_layout")
        self.part_panel_layout.setContentsMargins(0, 0, 8, 0)
        self.part_list_label = QLabel(self.part_panel)
        self.part_list_label.setObjectName(u"part_list_label")
        self.part_list_label.setStyleSheet(u"font-weight: bold; color: #202124;")

        self.part_panel_layout.addWidget(self.part_list_label)

        self.part_list = QListWidget(self.part_panel)
        self.part_list.setObjectName(u"part_list")
        self.part_list.setStyleSheet(u"QListWidget { border: 1px solid #dadce0; border-radius: 6px; background: #ffffff; }\n"
"QListWidget::item { padding: 8px 10px; }\n"
"QListWidget::item:selected { background: #e8f0fe; color: #174ea6; }")

        self.part_panel_layout.addWidget(self.part_list)

        self.test_splitter.addWidget(self.part_panel)
        self.question_panel = QWidget(self.test_splitter)
        self.question_panel.setObjectName(u"question_panel")
        self.question_panel_layout = QVBoxLayout(self.question_panel)
        self.question_panel_layout.setObjectName(u"question_panel_layout")
        self.question_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.test_scroll = QScrollArea(self.question_panel)
        self.test_scroll.setObjectName(u"test_scroll")
        self.test_scroll.setWidgetResizable(True)
        self.test_questions_container = QWidget()
        self.test_questions_container.setObjectName(u"test_questions_container")
        self.test_questions_container.setGeometry(QRect(0, 0, 758, 588))
        self.test_questions_layout = QVBoxLayout(self.test_questions_container)
        self.test_questions_layout.setObjectName(u"test_questions_layout")
        self.test_questions_layout.setContentsMargins(0, 0, 0, 0)
        self.test_scroll.setWidget(self.test_questions_container)

        self.question_panel_layout.addWidget(self.test_scroll)

        self.test_splitter.addWidget(self.question_panel)

        self.test_layout.addWidget(self.test_splitter)

        self.test_footer_layout = QHBoxLayout()
        self.test_footer_layout.setObjectName(u"test_footer_layout")

        self.test_layout.addLayout(self.test_footer_layout)

        self.stacked_widget.addWidget(self.test_page)
        self.result_page = QWidget()
        self.result_page.setObjectName(u"result_page")
        self.result_layout = QVBoxLayout(self.result_page)
        self.result_layout.setObjectName(u"result_layout")
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.addWidget(self.result_page)
        self.history_page = QWidget()
        self.history_page.setObjectName(u"history_page")
        self.history_layout = QVBoxLayout(self.history_page)
        self.history_layout.setObjectName(u"history_layout")
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.addWidget(self.history_page)
        self.dictation_page = QWidget()
        self.dictation_page.setObjectName(u"dictation_page")
        self.dictation_layout = QVBoxLayout(self.dictation_page)
        self.dictation_layout.setObjectName(u"dictation_layout")
        self.dictation_layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.addWidget(self.dictation_page)

        self.main_layout.addWidget(self.stacked_widget)


        self.retranslateUi(ExamTakeView)

        self.stacked_widget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(ExamTakeView)
    # setupUi

    def retranslateUi(self, ExamTakeView):
        ExamTakeView.setWindowTitle(QCoreApplication.translate("ExamTakeView", u"Exam", None))
        self.back_btn.setText(QCoreApplication.translate("ExamTakeView", u"Back", None))
        self.title_label.setText(QCoreApplication.translate("ExamTakeView", u"Exam", None))
        self.subtitle_label.setText("")
        self.timer_label.setText(QCoreApplication.translate("ExamTakeView", u"00:00", None))
        self.part_list_label.setText(QCoreApplication.translate("ExamTakeView", u"Parts", None))
    # retranslateUi

