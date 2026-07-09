# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'vocabulary_list_view.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_VocabularyListView(object):
    def setupUi(self, VocabularyListView:QWidget):
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

        self.search_input = QLineEdit(VocabularyListView)
        self.search_input.setObjectName(u"search_input")
        self.search_input.setMinimumSize(QSize(280, 0))

        self.header_layout.addWidget(self.search_input)


        self.main_layout.addLayout(self.header_layout)

        self.table = QTableWidget(VocabularyListView)
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
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setColumnCount(5)

        self.main_layout.addWidget(self.table)


        self.retranslateUi(VocabularyListView)

        QMetaObject.connectSlotsByName(VocabularyListView)
    # setupUi

    def retranslateUi(self, VocabularyListView:QWidget):
        VocabularyListView.setWindowTitle(QCoreApplication.translate("VocabularyListView", u"Vocabulary List", None))
        self.back_button.setText(QCoreApplication.translate("VocabularyListView", u"\u2190 Back", None))
        self.title_label.setText(QCoreApplication.translate("VocabularyListView", u"Vocabulary List", None))
        self.search_input.setPlaceholderText(QCoreApplication.translate("VocabularyListView", u"Search words, meanings, or context...", None))
        ___qtablewidgetitem = self.table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("VocabularyListView", u"Word", None))
        ___qtablewidgetitem1 = self.table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("VocabularyListView", u"Meaning", None))
        ___qtablewidgetitem2 = self.table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("VocabularyListView", u"Source Context", None))
        ___qtablewidgetitem3 = self.table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("VocabularyListView", u"Status", None))
        ___qtablewidgetitem4 = self.table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("VocabularyListView", u"Actions", None))
    # retranslateUi

