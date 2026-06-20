# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'exam_list_view.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_ExamListView(object):
    def setupUi(self, ExamListView):
        if not ExamListView.objectName():
            ExamListView.setObjectName(u"ExamListView")
        ExamListView.resize(800, 600)
        self.main_layout = QVBoxLayout(ExamListView)
        self.main_layout.setObjectName(u"main_layout")
        self.header_layout = QHBoxLayout()
        self.header_layout.setObjectName(u"header_layout")
        self.title_label = QLabel(ExamListView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 24px; font-weight: bold; color: #1a73e8;")

        self.header_layout.addWidget(self.title_label)

        self.search_input = QLineEdit(ExamListView)
        self.search_input.setObjectName(u"search_input")

        self.header_layout.addWidget(self.search_input)

        self.add_btn = QPushButton(ExamListView)
        self.add_btn.setObjectName(u"add_btn")
        self.add_btn.setStyleSheet(u"background-color: #1a73e8; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px;")

        self.header_layout.addWidget(self.add_btn)

        self.add_ext_btn = QPushButton(ExamListView)
        self.add_ext_btn.setObjectName(u"add_ext_btn")
        self.add_ext_btn.setStyleSheet(u"background-color: #34a853; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px;")

        self.header_layout.addWidget(self.add_ext_btn)


        self.main_layout.addLayout(self.header_layout)

        self.table = QTableWidget(ExamListView)
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

        self.main_layout.addWidget(self.table)


        self.retranslateUi(ExamListView)

        QMetaObject.connectSlotsByName(ExamListView)
    # setupUi

    def retranslateUi(self, ExamListView):
        ExamListView.setWindowTitle(QCoreApplication.translate("ExamListView", u"Exam List", None))
        self.title_label.setText(QCoreApplication.translate("ExamListView", u"Exam List", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("ExamListView", u"Search exams...", None))
        self.add_btn.setText(QCoreApplication.translate("ExamListView", u"Add Exam", None))
        self.add_ext_btn.setText(QCoreApplication.translate("ExamListView", u"Add External", None))
        ___qtablewidgetitem = self.table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ExamListView", u"Title", None))
        ___qtablewidgetitem1 = self.table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ExamListView", u"Duration (mins)", None))
        ___qtablewidgetitem2 = self.table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ExamListView", u"Published", None))
        ___qtablewidgetitem3 = self.table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ExamListView", u"Start", None))
        ___qtablewidgetitem4 = self.table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("ExamListView", u"Manage", None))
    # retranslateUi

