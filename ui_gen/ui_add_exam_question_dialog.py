# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_exam_question_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class Ui_AddExamQuestionDialog(object):
    def setupUi(self, AddExamQuestionDialog):
        if not AddExamQuestionDialog.objectName():
            AddExamQuestionDialog.setObjectName(u"AddExamQuestionDialog")
        AddExamQuestionDialog.resize(720, 760)
        AddExamQuestionDialog.setStyleSheet(u"QDialog { background-color: #f8f9fa; }\n"
"QLabel { font-size: 12px; color: #3c4043; }\n"
"QLineEdit, QTextEdit, QComboBox, QSpinBox {\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 6px;\n"
"    padding: 6px 8px;\n"
"    font-size: 12px;\n"
"    background-color: white;\n"
"}\n"
"QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #1a73e8; }\n"
"QGroupBox {\n"
"    font-weight: bold;\n"
"    font-size: 12px;\n"
"    color: #1a73e8;\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 8px;\n"
"    margin-top: 8px;\n"
"    padding-top: 10px;\n"
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
"QPushButton#cancel_btn, QPushButton#paste_image_btn {\n"
""
                        "    background-color: white;\n"
"    color: #3c4043;\n"
"    border: 1px solid #dadce0;\n"
"    border-radius: 6px;\n"
"    padding: 8px 14px;\n"
"    font-size: 12px;\n"
"}\n"
"QPushButton#cancel_btn:hover, QPushButton#paste_image_btn:hover { background-color: #f1f3f4; }")
        self.main_layout = QVBoxLayout(AddExamQuestionDialog)
        self.main_layout.setSpacing(12)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.header_label = QLabel(AddExamQuestionDialog)
        self.header_label.setObjectName(u"header_label")
        self.header_label.setStyleSheet(u"font-size: 15px; font-weight: bold; color: #202124;")

        self.main_layout.addWidget(self.header_label)

        self.context_group = QGroupBox(AddExamQuestionDialog)
        self.context_group.setObjectName(u"context_group")
        self.context_form = QFormLayout(self.context_group)
        self.context_form.setSpacing(8)
        self.context_form.setObjectName(u"context_form")
        self.part_label = QLabel(self.context_group)
        self.part_label.setObjectName(u"part_label")

        self.context_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.part_label)

        self.part_spin = QSpinBox(self.context_group)
        self.part_spin.setObjectName(u"part_spin")
        self.part_spin.setMinimum(1)
        self.part_spin.setMaximum(9)

        self.context_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.part_spin)

        self.context_type_label = QLabel(self.context_group)
        self.context_type_label.setObjectName(u"context_type_label")

        self.context_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.context_type_label)

        self.context_type_combo = QComboBox(self.context_group)
        self.context_type_combo.setObjectName(u"context_type_combo")

        self.context_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.context_type_combo)

        self.context_index_label = QLabel(self.context_group)
        self.context_index_label.setObjectName(u"context_index_label")

        self.context_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.context_index_label)

        self.context_index_spin = QSpinBox(self.context_group)
        self.context_index_spin.setObjectName(u"context_index_spin")
        self.context_index_spin.setMaximum(9999)

        self.context_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.context_index_spin)

        self.context_stack = QStackedWidget(self.context_group)
        self.context_stack.setObjectName(u"context_stack")
        self.text_page = QWidget()
        self.text_page.setObjectName(u"text_page")
        self.text_page_layout = QVBoxLayout(self.text_page)
        self.text_page_layout.setObjectName(u"text_page_layout")
        self.text_page_layout.setContentsMargins(0, 0, 0, 0)
        self.context_text_edit = QTextEdit(self.text_page)
        self.context_text_edit.setObjectName(u"context_text_edit")
        self.context_text_edit.setMinimumSize(QSize(0, 110))

        self.text_page_layout.addWidget(self.context_text_edit)

        self.context_stack.addWidget(self.text_page)
        self.audio_page = QWidget()
        self.audio_page.setObjectName(u"audio_page")
        self.audio_page_layout = QVBoxLayout(self.audio_page)
        self.audio_page_layout.setObjectName(u"audio_page_layout")
        self.audio_page_layout.setContentsMargins(0, 0, 0, 0)
        self.audio_context_edit = QTextEdit(self.audio_page)
        self.audio_context_edit.setObjectName(u"audio_context_edit")
        self.audio_context_edit.setMinimumSize(QSize(0, 110))

        self.audio_page_layout.addWidget(self.audio_context_edit)

        self.context_stack.addWidget(self.audio_page)
        self.image_page = QWidget()
        self.image_page.setObjectName(u"image_page")
        self.image_page_layout = QVBoxLayout(self.image_page)
        self.image_page_layout.setObjectName(u"image_page_layout")
        self.image_page_layout.setContentsMargins(0, 0, 0, 0)
        self.image_description_edit = QTextEdit(self.image_page)
        self.image_description_edit.setObjectName(u"image_description_edit")
        self.image_description_edit.setMinimumSize(QSize(0, 70))

        self.image_page_layout.addWidget(self.image_description_edit)

        self.image_drop_placeholder = QLabel(self.image_page)
        self.image_drop_placeholder.setObjectName(u"image_drop_placeholder")
        self.image_drop_placeholder.setMinimumSize(QSize(0, 180))
        self.image_drop_placeholder.setStyleSheet(u"border: 2px dashed #9aa0a6; border-radius: 6px; background: #f8f9fa; color: #5f6368; padding: 16px;")
        self.image_drop_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_page_layout.addWidget(self.image_drop_placeholder)

        self.image_button_layout = QHBoxLayout()
        self.image_button_layout.setObjectName(u"image_button_layout")
        self.paste_image_btn = QPushButton(self.image_page)
        self.paste_image_btn.setObjectName(u"paste_image_btn")

        self.image_button_layout.addWidget(self.paste_image_btn)

        self.image_button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.image_button_layout.addItem(self.image_button_spacer)


        self.image_page_layout.addLayout(self.image_button_layout)

        self.context_stack.addWidget(self.image_page)

        self.context_form.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.context_stack)


        self.main_layout.addWidget(self.context_group)

        self.question_group = QGroupBox(AddExamQuestionDialog)
        self.question_group.setObjectName(u"question_group")
        self.question_form = QFormLayout(self.question_group)
        self.question_form.setSpacing(8)
        self.question_form.setObjectName(u"question_form")
        self.question_number_label = QLabel(self.question_group)
        self.question_number_label.setObjectName(u"question_number_label")

        self.question_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.question_number_label)

        self.question_number_spin = QSpinBox(self.question_group)
        self.question_number_spin.setObjectName(u"question_number_spin")
        self.question_number_spin.setMinimum(1)
        self.question_number_spin.setMaximum(9999)

        self.question_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.question_number_spin)

        self.question_type_label = QLabel(self.question_group)
        self.question_type_label.setObjectName(u"question_type_label")

        self.question_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.question_type_label)

        self.question_type_combo = QComboBox(self.question_group)
        self.question_type_combo.setObjectName(u"question_type_combo")

        self.question_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.question_type_combo)

        self.answer_label = QLabel(self.question_group)
        self.answer_label.setObjectName(u"answer_label")

        self.question_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.answer_label)

        self.answer_combo = QComboBox(self.question_group)
        self.answer_combo.setObjectName(u"answer_combo")

        self.question_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.answer_combo)

        self.content_edit = QTextEdit(self.question_group)
        self.content_edit.setObjectName(u"content_edit")
        self.content_edit.setMinimumSize(QSize(0, 80))

        self.question_form.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.content_edit)

        self.option_a_label = QLabel(self.question_group)
        self.option_a_label.setObjectName(u"option_a_label")

        self.question_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.option_a_label)

        self.option_a_edit = QLineEdit(self.question_group)
        self.option_a_edit.setObjectName(u"option_a_edit")

        self.question_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.option_a_edit)

        self.option_b_label = QLabel(self.question_group)
        self.option_b_label.setObjectName(u"option_b_label")

        self.question_form.setWidget(5, QFormLayout.ItemRole.LabelRole, self.option_b_label)

        self.option_b_edit = QLineEdit(self.question_group)
        self.option_b_edit.setObjectName(u"option_b_edit")

        self.question_form.setWidget(5, QFormLayout.ItemRole.FieldRole, self.option_b_edit)

        self.option_c_label = QLabel(self.question_group)
        self.option_c_label.setObjectName(u"option_c_label")

        self.question_form.setWidget(6, QFormLayout.ItemRole.LabelRole, self.option_c_label)

        self.option_c_edit = QLineEdit(self.question_group)
        self.option_c_edit.setObjectName(u"option_c_edit")

        self.question_form.setWidget(6, QFormLayout.ItemRole.FieldRole, self.option_c_edit)

        self.option_d_label = QLabel(self.question_group)
        self.option_d_label.setObjectName(u"option_d_label")

        self.question_form.setWidget(7, QFormLayout.ItemRole.LabelRole, self.option_d_label)

        self.option_d_edit = QLineEdit(self.question_group)
        self.option_d_edit.setObjectName(u"option_d_edit")

        self.question_form.setWidget(7, QFormLayout.ItemRole.FieldRole, self.option_d_edit)


        self.main_layout.addWidget(self.question_group)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.button_spacer)

        self.cancel_btn = QPushButton(AddExamQuestionDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(AddExamQuestionDialog)
        self.save_btn.setObjectName(u"save_btn")

        self.button_layout.addWidget(self.save_btn)


        self.main_layout.addLayout(self.button_layout)


        self.retranslateUi(AddExamQuestionDialog)

        QMetaObject.connectSlotsByName(AddExamQuestionDialog)
    # setupUi

    def retranslateUi(self, AddExamQuestionDialog):
        AddExamQuestionDialog.setWindowTitle(QCoreApplication.translate("AddExamQuestionDialog", u"Add Exam Question", None))
        self.header_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Create Context and Question", None))
        self.context_group.setTitle(QCoreApplication.translate("AddExamQuestionDialog", u"Context", None))
        self.part_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Part:", None))
        self.context_type_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Type:", None))
        self.context_index_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Index:", None))
        self.context_text_edit.setPlaceholderText(QCoreApplication.translate("AddExamQuestionDialog", u"Context text or reading passage...", None))
        self.audio_context_edit.setPlaceholderText(QCoreApplication.translate("AddExamQuestionDialog", u"Transcript text or SRT-style lines...", None))
        self.image_description_edit.setPlaceholderText(QCoreApplication.translate("AddExamQuestionDialog", u"Brief diagram description or source text...", None))
        self.image_drop_placeholder.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Drop image here or press Ctrl+V", None))
        self.paste_image_btn.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Paste Image", None))
        self.question_group.setTitle(QCoreApplication.translate("AddExamQuestionDialog", u"Question", None))
        self.question_number_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Question No.:", None))
        self.question_type_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Type:", None))
        self.answer_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Correct Answer:", None))
        self.content_edit.setPlaceholderText(QCoreApplication.translate("AddExamQuestionDialog", u"Question stem...", None))
        self.option_a_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"A:", None))
        self.option_b_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"B:", None))
        self.option_c_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"C:", None))
        self.option_d_label.setText(QCoreApplication.translate("AddExamQuestionDialog", u"D:", None))
        self.cancel_btn.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Cancel", None))
        self.save_btn.setText(QCoreApplication.translate("AddExamQuestionDialog", u"Create", None))
    # retranslateUi

