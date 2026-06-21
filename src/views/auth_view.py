from PySide6.QtWidgets import QDialog, QMessageBox

from ui_gen.ui_auth_view import Ui_AuthView
from src.viewmodels.auth_viewmodel import AuthViewModel


class AuthView(QDialog):
    def __init__(self, viewmodel: AuthViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel

        self.ui = Ui_AuthView()
        self.ui.setupUi(self)
        self.setModal(True)
        self.setWindowTitle("Jun Edu Account")

        self._connect_signals()
        self.update_ui()

    def _connect_signals(self) -> None:
        self.ui.primary_button.clicked.connect(self._on_primary_clicked)
        self.ui.toggle_button.clicked.connect(self.viewmodel.toggle_mode)
        self.ui.password_input.returnPressed.connect(self._on_primary_clicked)
        self.ui.confirm_password_input.returnPressed.connect(self._on_primary_clicked)
        self.viewmodel.state_changed.connect(self.update_ui)
        self.viewmodel.authenticated.connect(self._on_authenticated)
        self.viewmodel.error_message.connect(self._show_error)
        self.viewmodel.info_message.connect(self._show_info)

    def update_ui(self) -> None:
        is_login = self.viewmodel.is_login_mode
        is_loading = self.viewmodel.is_loading

        self.ui.subtitle_label.setText(
            "Sign in to manage your exams" if is_login else "Create your Jun Edu account"
        )
        self.ui.primary_button.setText("Login" if is_login else "Register")
        self.ui.toggle_button.setText(
            "Create an account" if is_login else "Back to login"
        )
        self.ui.confirm_password_input.setVisible(not is_login)
        self.ui.loading_bar.setVisible(is_loading)
        self.ui.message_label.setText(self.viewmodel.status_text)

        self.ui.email_input.setEnabled(not is_loading)
        self.ui.password_input.setEnabled(not is_loading)
        self.ui.confirm_password_input.setEnabled(not is_loading)
        self.ui.primary_button.setEnabled(not is_loading)
        self.ui.toggle_button.setEnabled(not is_loading)

    def _on_primary_clicked(self) -> None:
        email = self.ui.email_input.text()
        password = self.ui.password_input.text()
        if self.viewmodel.is_login_mode:
            self.viewmodel.login(email, password)
            return

        self.viewmodel.register(
            email,
            password,
            self.ui.confirm_password_input.text(),
        )

    def _show_error(self, message: str) -> None:
        if message:
            QMessageBox.warning(self, "Authentication", message)

    def _show_info(self, message: str) -> None:
        if message:
            QMessageBox.information(self, "Authentication", message)

    def _on_authenticated(self, _email: str) -> None:
        self.accept()
