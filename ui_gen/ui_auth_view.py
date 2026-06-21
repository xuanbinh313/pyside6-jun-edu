# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'auth_view.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QProgressBar,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_AuthView(object):
    def setupUi(self, AuthView):
        if not AuthView.objectName():
            AuthView.setObjectName(u"AuthView")
        AuthView.resize(520, 460)
        AuthView.setStyleSheet(u"QWidget {\n"
"    background: #f7f9fc;\n"
"    color: #1f2937;\n"
"}\n"
"QLineEdit {\n"
"    background: #ffffff;\n"
"    border: 1px solid #cbd5e1;\n"
"    border-radius: 6px;\n"
"    padding: 10px 12px;\n"
"    min-height: 24px;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: #1a73e8;\n"
"}\n"
"QPushButton {\n"
"    border-radius: 6px;\n"
"    padding: 10px 14px;\n"
"}\n"
"QPushButton#primary_button {\n"
"    background: #1a73e8;\n"
"    color: #ffffff;\n"
"    font-weight: 600;\n"
"}\n"
"QPushButton#primary_button:disabled {\n"
"    background: #94a3b8;\n"
"}\n"
"QPushButton#toggle_button {\n"
"    background: transparent;\n"
"    color: #1a73e8;\n"
"    border: none;\n"
"}\n"
"QLabel#title_label {\n"
"    font-size: 28px;\n"
"    font-weight: 700;\n"
"    color: #1a73e8;\n"
"}\n"
"QLabel#subtitle_label {\n"
"    color: #64748b;\n"
"}\n"
"QLabel#message_label {\n"
"    color: #dc2626;\n"
"}\n"
"QProgressBar {\n"
"    border: none;\n"
"    background: #e2e8f0;\n"
"    max-height: 4px;\n"
"}\n"
"QProgressBa"
                        "r::chunk {\n"
"    background: #1a73e8;\n"
"}")
        self.page_layout = QVBoxLayout(AuthView)
        self.page_layout.setObjectName(u"page_layout")
        self.page_layout.setContentsMargins(40, 40, 40, 40)
        self.top_spacer = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.page_layout.addItem(self.top_spacer)

        self.form_layout = QVBoxLayout()
        self.form_layout.setSpacing(12)
        self.form_layout.setObjectName(u"form_layout")
        self.title_label = QLabel(AuthView)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.form_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(AuthView)
        self.subtitle_label.setObjectName(u"subtitle_label")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.form_layout.addWidget(self.subtitle_label)

        self.header_gap = QSpacerItem(20, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.form_layout.addItem(self.header_gap)

        self.email_input = QLineEdit(AuthView)
        self.email_input.setObjectName(u"email_input")
        self.email_input.setClearButtonEnabled(True)

        self.form_layout.addWidget(self.email_input)

        self.password_input = QLineEdit(AuthView)
        self.password_input.setObjectName(u"password_input")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setClearButtonEnabled(True)

        self.form_layout.addWidget(self.password_input)

        self.confirm_password_input = QLineEdit(AuthView)
        self.confirm_password_input.setObjectName(u"confirm_password_input")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setClearButtonEnabled(True)

        self.form_layout.addWidget(self.confirm_password_input)

        self.message_label = QLabel(AuthView)
        self.message_label.setObjectName(u"message_label")
        self.message_label.setWordWrap(True)

        self.form_layout.addWidget(self.message_label)

        self.loading_bar = QProgressBar(AuthView)
        self.loading_bar.setObjectName(u"loading_bar")
        self.loading_bar.setMinimum(0)
        self.loading_bar.setMaximum(0)
        self.loading_bar.setTextVisible(False)

        self.form_layout.addWidget(self.loading_bar)

        self.primary_button = QPushButton(AuthView)
        self.primary_button.setObjectName(u"primary_button")
        self.primary_button.setMinimumSize(QSize(0, 44))

        self.form_layout.addWidget(self.primary_button)

        self.toggle_button = QPushButton(AuthView)
        self.toggle_button.setObjectName(u"toggle_button")

        self.form_layout.addWidget(self.toggle_button)


        self.page_layout.addLayout(self.form_layout)

        self.bottom_spacer = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.page_layout.addItem(self.bottom_spacer)


        self.retranslateUi(AuthView)

        QMetaObject.connectSlotsByName(AuthView)
    # setupUi

    def retranslateUi(self, AuthView):
        AuthView.setWindowTitle(QCoreApplication.translate("AuthView", u"Jun Edu - Sign In", None))
        self.title_label.setText(QCoreApplication.translate("AuthView", u"Jun Edu", None))
        self.subtitle_label.setText(QCoreApplication.translate("AuthView", u"Sign in to manage your exams", None))
        self.email_input.setPlaceholderText(QCoreApplication.translate("AuthView", u"Email", None))
        self.password_input.setPlaceholderText(QCoreApplication.translate("AuthView", u"Password", None))
        self.confirm_password_input.setPlaceholderText(QCoreApplication.translate("AuthView", u"Confirm password", None))
        self.message_label.setText("")
        self.primary_button.setText(QCoreApplication.translate("AuthView", u"Login", None))
        self.toggle_button.setText(QCoreApplication.translate("AuthView", u"Create an account", None))
    # retranslateUi

