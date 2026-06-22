# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_groups_widget.ui'
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
    QSpacerItem, QTextBrowser, QVBoxLayout, QWidget)

class Ui_ExamGroupsWidget(object):
    def setupUi(self, ExamGroupsWidget):
        if not ExamGroupsWidget.objectName():
            ExamGroupsWidget.setObjectName(u"ExamGroupsWidget")
        ExamGroupsWidget.resize(800, 600)
        self.main_layout = QHBoxLayout(ExamGroupsWidget)
        self.main_layout.setSpacing(15)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.left_panel = QWidget(ExamGroupsWidget)
        self.left_panel.setObjectName(u"left_panel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.left_panel.sizePolicy().hasHeightForWidth())
        self.left_panel.setSizePolicy(sizePolicy)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setSpacing(6)
        self.left_layout.setObjectName(u"left_layout")
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.q_label_layout = QHBoxLayout()
        self.q_label_layout.setObjectName(u"q_label_layout")
        self.q_label = QLabel(self.left_panel)
        self.q_label.setObjectName(u"q_label")
        self.q_label.setStyleSheet(u"font-size: 16px; font-weight: bold; color: #1a73e8;")

        self.q_label_layout.addWidget(self.q_label)

        self.horizontalSpacer_left = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.q_label_layout.addItem(self.horizontalSpacer_left)

        self.import_q_btn = QPushButton(self.left_panel)
        self.import_q_btn.setObjectName(u"import_q_btn")
        self.import_q_btn.setMinimumSize(QSize(28, 28))
        self.import_q_btn.setMaximumSize(QSize(28, 28))

        self.q_label_layout.addWidget(self.import_q_btn)


        self.left_layout.addLayout(self.q_label_layout)

        self.filter_label = QLabel(self.left_panel)
        self.filter_label.setObjectName(u"filter_label")
        self.filter_label.setStyleSheet(u"font-size: 12px; font-weight: bold; color: #5f6368; margin-top: 4px;")

        self.left_layout.addWidget(self.filter_label)

        self.tag_filter_list = QListWidget(self.left_panel)
        self.tag_filter_list.setObjectName(u"tag_filter_list")
        self.tag_filter_list.setMaximumSize(QSize(16777215, 80))
        self.tag_filter_list.setStyleSheet(u"\n"
"            QListWidget {\n"
"                border: 1px solid #dadce0;\n"
"                border-radius: 6px;\n"
"                background-color: #f8f9fa;\n"
"                padding: 2px;\n"
"            }\n"
"            QListWidget::item {\n"
"                padding: 4px;\n"
"            }\n"
"        ")

        self.left_layout.addWidget(self.tag_filter_list)

        self.q_list = QListWidget(self.left_panel)
        self.q_list.setObjectName(u"q_list")
        self.q_list.setStyleSheet(u"\n"
"            QListWidget {\n"
"                border: 1px solid #dadce0;\n"
"                border-radius: 6px;\n"
"                background-color: #ffffff;\n"
"            }\n"
"            QListWidget::item {\n"
"                padding: 0 10px;\n"
"                border-bottom: 1px solid #f1f3f4;\n"
"            }\n"
"            QListWidget::item:selected {\n"
"                background-color: #e8f0fe;\n"
"                color: #1a73e8;\n"
"                border: none;\n"
"            }\n"
"\n"
"            QListWidget {\n"
"                outline: 0;\n"
"            }\n"
"        ")

        self.left_layout.addWidget(self.q_list)


        self.main_layout.addWidget(self.left_panel)

        self.right_outer = QWidget(ExamGroupsWidget)
        self.right_outer.setObjectName(u"right_outer")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(3)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.right_outer.sizePolicy().hasHeightForWidth())
        self.right_outer.setSizePolicy(sizePolicy1)
        self.right_outer_layout = QVBoxLayout(self.right_outer)
        self.right_outer_layout.setSpacing(8)
        self.right_outer_layout.setObjectName(u"right_outer_layout")
        self.right_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.title_outer = QHBoxLayout()
        self.title_outer.setObjectName(u"title_outer")
        self.title_label = QLabel(self.right_outer)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 16px; font-weight: bold; color: #3c4043;")
        self.title_label.setWordWrap(True)

        self.title_outer.addWidget(self.title_label)


        self.right_outer_layout.addLayout(self.title_outer)

        self.listen_widget = QWidget(self.right_outer)
        self.listen_widget.setObjectName(u"listen_widget")
        self.listen_widget.setVisible(False)
        self.listen_sub = QHBoxLayout(self.listen_widget)
        self.listen_sub.setObjectName(u"listen_sub")
        self.listen_sub.setContentsMargins(0, 5, 0, 5)
        self.listen_btn = QPushButton(self.listen_widget)
        self.listen_btn.setObjectName(u"listen_btn")
        self.listen_btn.setStyleSheet(u"\n"
"            QPushButton {\n"
"                background-color: #1a73e8; color: white;\n"
"                font-weight: bold; padding: 8px 16px; border-radius: 6px;\n"
"            }\n"
"            QPushButton:hover { background-color: #1558b0; }\n"
"        ")

        self.listen_sub.addWidget(self.listen_btn)

        self.status_label = QLabel(self.listen_widget)
        self.status_label.setObjectName(u"status_label")
        self.status_label.setStyleSheet(u"color: #5f6368; font-style: italic; font-size: 12px;")

        self.listen_sub.addWidget(self.status_label)

        self.horizontalSpacer_listen = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.listen_sub.addItem(self.horizontalSpacer_listen)


        self.right_outer_layout.addWidget(self.listen_widget)

        self.passage_browser = QTextBrowser(self.right_outer)
        self.passage_browser.setObjectName(u"passage_browser")
        self.passage_browser.setVisible(False)
        self.passage_browser.setStyleSheet(u"\n"
"            QTextBrowser {\n"
"                border: 1px solid #dadce0; border-radius: 6px;\n"
"                background-color: #fffde7; padding: 10px;\n"
"                font-size: 13px; line-height: 1.6;\n"
"            }\n"
"        ")
        self.passage_browser.setOpenLinks(False)

        self.right_outer_layout.addWidget(self.passage_browser)

        self.transcript_label = QLabel(self.right_outer)
        self.transcript_label.setObjectName(u"transcript_label")
        self.transcript_label.setVisible(False)
        self.transcript_label.setStyleSheet(u"font-size: 14px; font-weight: bold; color: #1a73e8;")

        self.right_outer_layout.addWidget(self.transcript_label)

        self.transcript_browser = QTextBrowser(self.right_outer)
        self.transcript_browser.setObjectName(u"transcript_browser")
        self.transcript_browser.setVisible(False)
        self.transcript_browser.setStyleSheet(u"\n"
"            QTextBrowser {\n"
"                border: 1px solid #dadce0; border-radius: 6px;\n"
"                background-color: #ffffff; padding: 10px;\n"
"                font-size: 13px; line-height: 1.5;\n"
"            }\n"
"        ")

        self.right_outer_layout.addWidget(self.transcript_browser)

        self.options_scroll = QScrollArea(self.right_outer)
        self.options_scroll.setObjectName(u"options_scroll")
        self.options_scroll.setStyleSheet(u"QScrollArea { border: none; }")
        self.options_scroll.setWidgetResizable(True)
        self.options_container = QWidget()
        self.options_container.setObjectName(u"options_container")
        self.options_container.setGeometry(QRect(0, 0, 574, 548))
        self.options_layout = QVBoxLayout(self.options_container)
        self.options_layout.setSpacing(12)
        self.options_layout.setObjectName(u"options_layout")
        self.options_layout.setContentsMargins(4, 4, 4, 4)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.options_layout.addItem(self.verticalSpacer)

        self.options_scroll.setWidget(self.options_container)

        self.right_outer_layout.addWidget(self.options_scroll)


        self.main_layout.addWidget(self.right_outer)


        self.retranslateUi(ExamGroupsWidget)

        QMetaObject.connectSlotsByName(ExamGroupsWidget)
    # setupUi

    def retranslateUi(self, ExamGroupsWidget):
        ExamGroupsWidget.setWindowTitle(QCoreApplication.translate("ExamGroupsWidget", u"Groups & Questions", None))
        self.q_label.setText(QCoreApplication.translate("ExamGroupsWidget", u"Exam Questions", None))
#if QT_CONFIG(tooltip)
        self.import_q_btn.setToolTip(QCoreApplication.translate("ExamGroupsWidget", u"Import Questions from CSV", None))
#endif // QT_CONFIG(tooltip)
        self.filter_label.setText(QCoreApplication.translate("ExamGroupsWidget", u"Filter by Tags:", None))
        self.title_label.setText(QCoreApplication.translate("ExamGroupsWidget", u"Select a question to view details", None))
        self.listen_btn.setText(QCoreApplication.translate("ExamGroupsWidget", u"Listen to this segment", None))
        self.status_label.setText("")
        self.transcript_label.setText(QCoreApplication.translate("ExamGroupsWidget", u"Transcript Context", None))
    # retranslateUi

