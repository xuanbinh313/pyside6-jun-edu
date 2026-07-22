# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'vocabulary_list_view.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_VocabularyListView(object):
    def setupUi(self, VocabularyListView: QWidget):
        if not VocabularyListView.objectName():
            VocabularyListView.setObjectName(u"VocabularyListView")
        VocabularyListView.resize(1000, 650)
        self.main_layout = QVBoxLayout(VocabularyListView)
        self.main_layout.setObjectName(u"main_layout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.back_button = QPushButton(VocabularyListView)
        self.back_button.setObjectName(u"back_button")

        self.header_layout.addWidget(self.back_button)

        self.title_label = QLabel(VocabularyListView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 24px; font-weight: bold; color: #1a73e8;")

        self.header_layout.addWidget(self.title_label)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)

        self.translate_button = QPushButton(VocabularyListView)
        self.translate_button.setObjectName(u"translate_button")

        self.header_layout.addWidget(self.translate_button)

        self.due_only_checkbox = QCheckBox(VocabularyListView)
        self.due_only_checkbox.setObjectName(u"due_only_checkbox")

        self.header_layout.addWidget(self.due_only_checkbox)

        self.search_input = QLineEdit(VocabularyListView)
        self.search_input.setObjectName(u"search_input")
        self.search_input.setMinimumSize(QSize(280, 0))

        self.header_layout.addWidget(self.search_input)


        self.main_layout.addLayout(self.header_layout)

        self.scroll_area = QScrollArea(VocabularyListView)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_contents = QWidget()
        self.scroll_contents.setObjectName(u"scroll_contents")
        self.scroll_contents.setGeometry(QRect(0, 0, 980, 580))
        self.cards_layout = QVBoxLayout(self.scroll_contents)
        self.cards_layout.setObjectName(u"cards_layout")
        self.scroll_area.setWidget(self.scroll_contents)

        self.main_layout.addWidget(self.scroll_area)


        self.retranslateUi(VocabularyListView)

        QMetaObject.connectSlotsByName(VocabularyListView)
    # setupUi

    def retranslateUi(self, VocabularyListView: QWidget):
        VocabularyListView.setWindowTitle(QCoreApplication.translate("VocabularyListView", u"Vocabulary List", None))
        self.back_button.setText(QCoreApplication.translate("VocabularyListView", u"Back", None))
        self.title_label.setText(QCoreApplication.translate("VocabularyListView", u"Vocabulary List", None))
        self.translate_button.setText(QCoreApplication.translate("VocabularyListView", u"AI Translate Empty", None))
        self.due_only_checkbox.setText(QCoreApplication.translate("VocabularyListView", u"Due Today", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("VocabularyListView", u"Search words, meanings, or context...", None))
    # retranslateUi

