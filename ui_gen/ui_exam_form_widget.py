# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_form_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpinBox, QTextEdit, QVBoxLayout, QWidget)

class Ui_ExamFormWidget(object):
    def setupUi(self, ExamFormWidget: QWidget):
        if not ExamFormWidget.objectName():
            ExamFormWidget.setObjectName(u"ExamFormWidget")
        ExamFormWidget.resize(650, 420)
        self.main_layout = QVBoxLayout(ExamFormWidget)
        self.main_layout.setObjectName(u"main_layout")
        self.form_layout = QFormLayout()
        self.form_layout.setObjectName(u"form_layout")
        self.title_label = QLabel(ExamFormWidget)
        self.title_label.setObjectName(u"title_label")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.title_label)

        self.title_input = QLineEdit(ExamFormWidget)
        self.title_input.setObjectName(u"title_input")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.title_input)

        self.description_label = QLabel(ExamFormWidget)
        self.description_label.setObjectName(u"description_label")

        self.form_layout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.description_label)

        self.description_input = QTextEdit(ExamFormWidget)
        self.description_input.setObjectName(u"description_input")

        self.form_layout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.description_input)

        self.audio_label = QLabel(ExamFormWidget)
        self.audio_label.setObjectName(u"audio_label")

        self.form_layout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.audio_label)

        self.audio_layout = QHBoxLayout()
        self.audio_layout.setObjectName(u"audio_layout")
        self.audio_input = QLineEdit(ExamFormWidget)
        self.audio_input.setObjectName(u"audio_input")

        self.audio_layout.addWidget(self.audio_input)

        self.upload_audio_btn = QPushButton(ExamFormWidget)
        self.upload_audio_btn.setObjectName(u"upload_audio_btn")

        self.audio_layout.addWidget(self.upload_audio_btn)


        self.form_layout.setLayout(2, QFormLayout.ItemRole.FieldRole, self.audio_layout)

        self.duration_label = QLabel(ExamFormWidget)
        self.duration_label.setObjectName(u"duration_label")

        self.form_layout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.duration_label)

        self.duration_input = QSpinBox(ExamFormWidget)
        self.duration_input.setObjectName(u"duration_input")
        self.duration_input.setMaximum(1000)

        self.form_layout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.duration_input)

        self.published_label = QLabel(ExamFormWidget)
        self.published_label.setObjectName(u"published_label")

        self.form_layout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.published_label)

        self.published_checkbox = QCheckBox(ExamFormWidget)
        self.published_checkbox.setObjectName(u"published_checkbox")

        self.form_layout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.published_checkbox)


        self.main_layout.addLayout(self.form_layout)

        self.action_layout = QHBoxLayout()
        self.action_layout.setObjectName(u"action_layout")
        self.attach_srt_btn = QPushButton(ExamFormWidget)
        self.attach_srt_btn.setObjectName(u"attach_srt_btn")

        self.action_layout.addWidget(self.attach_srt_btn)

        self.import_csv_btn = QPushButton(ExamFormWidget)
        self.import_csv_btn.setObjectName(u"import_csv_btn")

        self.action_layout.addWidget(self.import_csv_btn)


        self.main_layout.addLayout(self.action_layout)

        self.save_btn = QPushButton(ExamFormWidget)
        self.save_btn.setObjectName(u"save_btn")
        self.save_btn.setStyleSheet(u"background-color: #34a853; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")

        self.main_layout.addWidget(self.save_btn)


        self.retranslateUi(ExamFormWidget)

        QMetaObject.connectSlotsByName(ExamFormWidget)
    # setupUi

    def retranslateUi(self, ExamFormWidget: QWidget):
        ExamFormWidget.setWindowTitle(QCoreApplication.translate("ExamFormWidget", u"Exam Details", None))
        self.title_label.setText(QCoreApplication.translate("ExamFormWidget", u"Title:", None))
        self.description_label.setText(QCoreApplication.translate("ExamFormWidget", u"Description:", None))
        self.audio_label.setText(QCoreApplication.translate("ExamFormWidget", u"Audio Name:", None))
        self.upload_audio_btn.setText(QCoreApplication.translate("ExamFormWidget", u"Upload Audio", None))
        self.duration_label.setText(QCoreApplication.translate("ExamFormWidget", u"Duration (minutes):", None))
        self.published_label.setText(QCoreApplication.translate("ExamFormWidget", u"Published:", None))
        self.published_checkbox.setText("")
        self.attach_srt_btn.setText(QCoreApplication.translate("ExamFormWidget", u"Attach SRT", None))
        self.import_csv_btn.setText(QCoreApplication.translate("ExamFormWidget", u"Import CSV", None))
        self.save_btn.setText(QCoreApplication.translate("ExamFormWidget", u"Save Details", None))
    # retranslateUi

