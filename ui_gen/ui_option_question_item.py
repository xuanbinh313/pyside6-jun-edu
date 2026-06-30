# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'option_question_item.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class Ui_OptionQuestionItem(object):
    def setupUi(self, OptionQuestionItem: QWidget):
        if not OptionQuestionItem.objectName():
            OptionQuestionItem.setObjectName(u"OptionQuestionItem")
        OptionQuestionItem.resize(400, 200)
        self.main_layout = QVBoxLayout(OptionQuestionItem)
        self.main_layout.setSpacing(4)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(4)
        self.header_layout.setObjectName(u"header_layout")
        self.stem = QLabel(OptionQuestionItem)
        self.stem.setObjectName(u"stem")
        self.stem.setWordWrap(True)

        self.header_layout.addWidget(self.stem)

        self.edit_q_btn = QPushButton(OptionQuestionItem)
        self.edit_q_btn.setObjectName(u"edit_q_btn")

        self.header_layout.addWidget(self.edit_q_btn)

        self.tag_btn = QPushButton(OptionQuestionItem)
        self.tag_btn.setObjectName(u"tag_btn")

        self.header_layout.addWidget(self.tag_btn)

        self.select_audio_btn = QPushButton(OptionQuestionItem)
        self.select_audio_btn.setObjectName(u"select_audio_btn")

        self.header_layout.addWidget(self.select_audio_btn)


        self.main_layout.addLayout(self.header_layout)

        self.options_layout = QVBoxLayout()
        self.options_layout.setSpacing(4)
        self.options_layout.setObjectName(u"options_layout")

        self.main_layout.addLayout(self.options_layout)

        self.result_label = QLabel(OptionQuestionItem)
        self.result_label.setObjectName(u"result_label")

        self.main_layout.addWidget(self.result_label)

        self.check_btn = QPushButton(OptionQuestionItem)
        self.check_btn.setObjectName(u"check_btn")

        self.main_layout.addWidget(self.check_btn)


        self.retranslateUi(OptionQuestionItem)

        QMetaObject.connectSlotsByName(OptionQuestionItem)
    # setupUi

    def retranslateUi(self, OptionQuestionItem: QWidget):
        OptionQuestionItem.setWindowTitle(QCoreApplication.translate("OptionQuestionItem", u"OptionQuestionItem", None))
        self.stem.setText(QCoreApplication.translate("OptionQuestionItem", u"Question Stem", None))
        self.edit_q_btn.setText("")
        self.tag_btn.setText("")
        self.select_audio_btn.setText("")
        self.result_label.setText("")
        self.check_btn.setText(QCoreApplication.translate("OptionQuestionItem", u"Check Answer", None))
    # retranslateUi

