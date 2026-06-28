# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_groups_item.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class Ui_ExamGroupsItem(object):
    def setupUi(self, ExamGroupsItem):
        if not ExamGroupsItem.objectName():
            ExamGroupsItem.setObjectName(u"ExamGroupsItem")
        ExamGroupsItem.resize(400, 300)
        self.horizontalLayoutWidget = QWidget(ExamGroupsItem)
        self.horizontalLayoutWidget.setObjectName(u"horizontalLayoutWidget")
        self.horizontalLayoutWidget.setGeometry(QRect(70, 40, 281, 121))
        self.horizontalLayout = QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.horizontalLayoutWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.pushButton = QPushButton(self.horizontalLayoutWidget)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout.addWidget(self.pushButton)


        self.retranslateUi(ExamGroupsItem)

        QMetaObject.connectSlotsByName(ExamGroupsItem)
    # setupUi

    def retranslateUi(self, ExamGroupsItem):
        ExamGroupsItem.setWindowTitle(QCoreApplication.translate("ExamGroupsItem", u"ExamGroupsItem", None))
        self.label.setText(QCoreApplication.translate("ExamGroupsItem", u"TextLabel", None))
        self.pushButton.setText(QCoreApplication.translate("ExamGroupsItem", u"PushButton", None))
    # retranslateUi

