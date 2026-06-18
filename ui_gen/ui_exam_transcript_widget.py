# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_transcript_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, Qt)
from PySide6.QtWidgets import (QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSlider, QSpacerItem,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

class Ui_ExamTranscriptWidget(object):
    def setupUi(self, ExamTranscriptWidget):
        if not ExamTranscriptWidget.objectName():
            ExamTranscriptWidget.setObjectName(u"ExamTranscriptWidget")
        ExamTranscriptWidget.resize(600, 400)
        self.verticalLayout = QVBoxLayout(ExamTranscriptWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.audio_controls = QHBoxLayout()
        self.audio_controls.setObjectName(u"audio_controls")
        self.play_pause_btn = QPushButton(ExamTranscriptWidget)
        self.play_pause_btn.setObjectName(u"play_pause_btn")

        self.audio_controls.addWidget(self.play_pause_btn)

        self.delay_label = QLabel(ExamTranscriptWidget)
        self.delay_label.setObjectName(u"delay_label")

        self.audio_controls.addWidget(self.delay_label)

        self.delay_spin = QSpinBox(ExamTranscriptWidget)
        self.delay_spin.setObjectName(u"delay_spin")
        self.delay_spin.setMaximum(10)
        self.delay_spin.setValue(3)

        self.audio_controls.addWidget(self.delay_spin)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.audio_controls.addItem(self.horizontalSpacer)

        self.save_btn = QPushButton(ExamTranscriptWidget)
        self.save_btn.setObjectName(u"save_btn")
        self.save_btn.setVisible(False)

        self.audio_controls.addWidget(self.save_btn)


        self.verticalLayout.addLayout(self.audio_controls)

        self.seek_layout = QHBoxLayout()
        self.seek_layout.setObjectName(u"seek_layout")
        self.time_current_label = QLabel(ExamTranscriptWidget)
        self.time_current_label.setObjectName(u"time_current_label")
        self.time_current_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.seek_layout.addWidget(self.time_current_label)

        self.seek_slider = QSlider(ExamTranscriptWidget)
        self.seek_slider.setObjectName(u"seek_slider")
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(1000)
        self.seek_slider.setOrientation(Qt.Orientation.Horizontal)

        self.seek_layout.addWidget(self.seek_slider)

        self.time_total_label = QLabel(ExamTranscriptWidget)
        self.time_total_label.setObjectName(u"time_total_label")

        self.seek_layout.addWidget(self.time_total_label)


        self.verticalLayout.addLayout(self.seek_layout)

        self.title_label = QLabel(ExamTranscriptWidget)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.table = QTableWidget(ExamTranscriptWidget)
        if (self.table.columnCount() < 5):
            self.table.setColumnCount(5)
        __qtablewidgetitem = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        self.table.setObjectName(u"table")
        self.table.setColumnCount(5)

        self.verticalLayout.addWidget(self.table)


        self.retranslateUi(ExamTranscriptWidget)

        QMetaObject.connectSlotsByName(ExamTranscriptWidget)
    # setupUi

    def retranslateUi(self, ExamTranscriptWidget):
        ExamTranscriptWidget.setWindowTitle(QCoreApplication.translate("ExamTranscriptWidget", u"Exam Transcript", None))
        self.play_pause_btn.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Play/Pause", None))
        self.delay_label.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Delay (s):", None))
        self.save_btn.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Save Changes", None))
        self.time_current_label.setText(QCoreApplication.translate("ExamTranscriptWidget", u"0:00", None))
        self.time_total_label.setText(QCoreApplication.translate("ExamTranscriptWidget", u"0:00", None))
        self.title_label.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Transcript Chunks", None))
        ___qtablewidgetitem = self.table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Index", None))
        ___qtablewidgetitem1 = self.table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Start Time", None))
        ___qtablewidgetitem2 = self.table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ExamTranscriptWidget", u"End Time", None))
        ___qtablewidgetitem3 = self.table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Text", None))
        ___qtablewidgetitem4 = self.table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("ExamTranscriptWidget", u"Actions", None))
    # retranslateUi

