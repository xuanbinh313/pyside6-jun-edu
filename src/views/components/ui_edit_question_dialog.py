# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_question_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize)
from PySide6.QtWidgets import (QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTextEdit,
    QVBoxLayout)

class Ui_EditQuestionDialog(object):
    def setupUi(self, EditQuestionDialog):
        if not EditQuestionDialog.objectName():
            EditQuestionDialog.setObjectName(u"EditQuestionDialog")
        EditQuestionDialog.resize(640, 520)
        EditQuestionDialog.setStyleSheet(u"QDialog { background-color: #f8f9fa; }\n"
"QLabel { font-size: 12px; color: #3c4043; }\n"
"QLineEdit, QTextEdit, QComboBox {\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 6px;\n"
"    padding: 6px 8px;\n"
"    font-size: 12px;\n"
"    background-color: white;\n"
"}\n"
"QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #1a73e8; }\n"
"QGroupBox {\n"
"    font-weight: bold;\n"
"    font-size: 12px;\n"
"    color: #1a73e8;\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 8px;\n"
"    margin-top: 8px;\n"
"    padding-top: 8px;\n"
"}\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    left: 10px;\n"
"    padding: 0 4px;\n"
"}\n"
"QPushButton#save_btn {\n"
"    background-color: #1a73e8;\n"
"    color: white;\n"
"    font-weight: bold;\n"
"    border-radius: 6px;\n"
"    padding: 8px 20px;\n"
"    font-size: 12px;\n"
"}\n"
"QPushButton#save_btn:hover { background-color: #1558b0; }\n"
"QPushButton#cancel_btn {\n"
"    background-color: white;\n"
"    color: #3c4043;\n"
""
                        "    border: 1px solid #dadce0;\n"
"    border-radius: 6px;\n"
"    padding: 8px 20px;\n"
"    font-size: 12px;\n"
"}\n"
"QPushButton#cancel_btn:hover { background-color: #f1f3f4; }")
        self.main_layout = QVBoxLayout(EditQuestionDialog)
        self.main_layout.setSpacing(14)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.header_label = QLabel(EditQuestionDialog)
        self.header_label.setObjectName(u"header_label")
        self.header_label.setStyleSheet(u"font-size: 15px; font-weight: bold; color: #202124;")

        self.main_layout.addWidget(self.header_label)

        self.meta_group = QGroupBox(EditQuestionDialog)
        self.meta_group.setObjectName(u"meta_group")
        self.meta_form = QFormLayout(self.meta_group)
        self.meta_form.setSpacing(8)
        self.meta_form.setObjectName(u"meta_form")
        self.part_label = QLabel(self.meta_group)
        self.part_label.setObjectName(u"part_label")

        self.meta_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.part_label)

        self.part_combo = QComboBox(self.meta_group)
        self.part_combo.setObjectName(u"part_combo")

        self.meta_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.part_combo)

        self.answer_label = QLabel(self.meta_group)
        self.answer_label.setObjectName(u"answer_label")

        self.meta_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.answer_label)

        self.answer_combo = QComboBox(self.meta_group)
        self.answer_combo.setObjectName(u"answer_combo")

        self.meta_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.answer_combo)


        self.main_layout.addWidget(self.meta_group)

        self.content_group = QGroupBox(EditQuestionDialog)
        self.content_group.setObjectName(u"content_group")
        self.content_layout = QVBoxLayout(self.content_group)
        self.content_layout.setObjectName(u"content_layout")
        self.content_edit = QTextEdit(self.content_group)
        self.content_edit.setObjectName(u"content_edit")
        self.content_edit.setMinimumSize(QSize(0, 80))
        self.content_edit.setMaximumSize(QSize(16777215, 80))

        self.content_layout.addWidget(self.content_edit)


        self.main_layout.addWidget(self.content_group)

        self.options_group = QGroupBox(EditQuestionDialog)
        self.options_group.setObjectName(u"options_group")
        self.options_form = QFormLayout(self.options_group)
        self.options_form.setSpacing(8)
        self.options_form.setObjectName(u"options_form")
        self.option_a_label = QLabel(self.options_group)
        self.option_a_label.setObjectName(u"option_a_label")

        self.options_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.option_a_label)

        self.option_a_edit = QLineEdit(self.options_group)
        self.option_a_edit.setObjectName(u"option_a_edit")

        self.options_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.option_a_edit)

        self.option_b_label = QLabel(self.options_group)
        self.option_b_label.setObjectName(u"option_b_label")

        self.options_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.option_b_label)

        self.option_b_edit = QLineEdit(self.options_group)
        self.option_b_edit.setObjectName(u"option_b_edit")

        self.options_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.option_b_edit)

        self.option_c_label = QLabel(self.options_group)
        self.option_c_label.setObjectName(u"option_c_label")

        self.options_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.option_c_label)

        self.option_c_edit = QLineEdit(self.options_group)
        self.option_c_edit.setObjectName(u"option_c_edit")

        self.options_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.option_c_edit)

        self.option_d_label = QLabel(self.options_group)
        self.option_d_label.setObjectName(u"option_d_label")

        self.options_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.option_d_label)

        self.option_d_edit = QLineEdit(self.options_group)
        self.option_d_edit.setObjectName(u"option_d_edit")

        self.options_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.option_d_edit)


        self.main_layout.addWidget(self.options_group)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.button_spacer)

        self.cancel_btn = QPushButton(EditQuestionDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(EditQuestionDialog)
        self.save_btn.setObjectName(u"save_btn")

        self.button_layout.addWidget(self.save_btn)


        self.main_layout.addLayout(self.button_layout)


        self.retranslateUi(EditQuestionDialog)

        QMetaObject.connectSlotsByName(EditQuestionDialog)
    # setupUi

    def retranslateUi(self, EditQuestionDialog):
        EditQuestionDialog.setWindowTitle(QCoreApplication.translate("EditQuestionDialog", u"Edit Question", None))
        self.header_label.setText(QCoreApplication.translate("EditQuestionDialog", u"Editing Question", None))
        self.meta_group.setTitle(QCoreApplication.translate("EditQuestionDialog", u"Meta", None))
        self.part_label.setText(QCoreApplication.translate("EditQuestionDialog", u"Part:", None))
        self.answer_label.setText(QCoreApplication.translate("EditQuestionDialog", u"Correct Answer:", None))
        self.content_group.setTitle(QCoreApplication.translate("EditQuestionDialog", u"Question Content", None))
        self.content_edit.setPlaceholderText(QCoreApplication.translate("EditQuestionDialog", u"Enter question text here...", None))
        self.options_group.setTitle(QCoreApplication.translate("EditQuestionDialog", u"Options (A / B / C / D)", None))
        self.option_a_label.setText(QCoreApplication.translate("EditQuestionDialog", u"A:", None))
        self.option_a_edit.setPlaceholderText(QCoreApplication.translate("EditQuestionDialog", u"Option A...", None))
        self.option_b_label.setText(QCoreApplication.translate("EditQuestionDialog", u"B:", None))
        self.option_b_edit.setPlaceholderText(QCoreApplication.translate("EditQuestionDialog", u"Option B...", None))
        self.option_c_label.setText(QCoreApplication.translate("EditQuestionDialog", u"C:", None))
        self.option_c_edit.setPlaceholderText(QCoreApplication.translate("EditQuestionDialog", u"Option C...", None))
        self.option_d_label.setText(QCoreApplication.translate("EditQuestionDialog", u"D:", None))
        self.option_d_edit.setPlaceholderText(QCoreApplication.translate("EditQuestionDialog", u"Option D...", None))
        self.cancel_btn.setText(QCoreApplication.translate("EditQuestionDialog", u"Cancel", None))
        self.save_btn.setText(QCoreApplication.translate("EditQuestionDialog", u"Save Changes", None))
    # retranslateUi

