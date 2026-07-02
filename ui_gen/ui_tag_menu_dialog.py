# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tag_menu_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QDialog


class Ui_TagMenuDialog(object):
    def setupUi(self, TagMenuDialog: QDialog):
        if not TagMenuDialog.objectName():
            TagMenuDialog.setObjectName(u"TagMenuDialog")
        TagMenuDialog.resize(200, 160)
        TagMenuDialog.setStyleSheet(u"QDialog {\n"
"    border: 1px solid #dadce0;\n"
"    background-color: white;\n"
"    border-radius: 6px;\n"
"}")
        self.main_layout = QVBoxLayout(TagMenuDialog)
        self.main_layout.setSpacing(6)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.title_label = QLabel(TagMenuDialog)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-weight: bold; color: #1a73e8; font-size: 12px;")

        self.main_layout.addWidget(self.title_label)

        self.tags_layout = QVBoxLayout()
        self.tags_layout.setSpacing(4)
        self.tags_layout.setObjectName(u"tags_layout")

        self.main_layout.addLayout(self.tags_layout)

        self.new_tag_input = QLineEdit(TagMenuDialog)
        self.new_tag_input.setObjectName(u"new_tag_input")
        self.new_tag_input.setStyleSheet(u"QLineEdit {\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 4px;\n"
"    padding: 4px;\n"
"    font-size: 11px;\n"
"}")

        self.main_layout.addWidget(self.new_tag_input)


        self.retranslateUi(TagMenuDialog)

        QMetaObject.connectSlotsByName(TagMenuDialog)
    # setupUi

    def retranslateUi(self, TagMenuDialog: QDialog):
        TagMenuDialog.setWindowTitle(QCoreApplication.translate("TagMenuDialog", u"Manage Tags", None))
        self.title_label.setText(QCoreApplication.translate("TagMenuDialog", u"Manage Tags", None))
        self.new_tag_input.setPlaceholderText(QCoreApplication.translate("TagMenuDialog", u"Add new tag...", None))
    # retranslateUi

