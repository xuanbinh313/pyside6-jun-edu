# Add current directory to path if needed, but normally running from jun-edu is fine.
import os
import sys

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QInputDialog, QMainWindow, QMenu,
                               QMessageBox, QSystemTrayIcon)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.repositories.sqlite.database import init_db
from src.viewmodels.auth_viewmodel import AuthViewModel
from src.viewmodels.exam_add_external_viewmodel import ExamAddExternalViewModel
from src.viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from src.viewmodels.exam_list_viewmodel import ExamListViewModel
from src.viewmodels.exam_take_viewmodel import ExamTakeViewModel
from src.viewmodels.reminder_viewmodel import ReminderViewModel
from src.viewmodels.sync_viewmodel import SyncViewModel
from src.views.auth_view import AuthView
from src.views.exam_add_external_view import ExamAddExternalView
from src.views.exam_details_view import ExamDetailsView
from src.views.exam_list_view import ExamListView
from src.views.exam_take_view import ExamTakeView
from ui_gen.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.auth_viewmodel = AuthViewModel()
        self.reminder_viewmodel = ReminderViewModel()
        self.sync_viewmodel = SyncViewModel()
        self.auth_dialog = None
        
        self.stacked_widget = self.ui.stacked_widget
        
        self.list_viewmodel = ExamListViewModel()
        self.list_view = ExamListView(
            self.list_viewmodel,
            self.navigate_to_details,
            self.navigate_to_take_exam,
        )
        
        self.stacked_widget.addWidget(self.list_view)
        
        self.close_event_minutes = 10
        self.setup_menu_bar()
        
        self.setup_system_tray()
        self.setup_mvvm_connections()
        self.auth_viewmodel.check_saved_session()
        
    def navigate_to_details(self, exam_id):
        if exam_id == "EXTERNAL":
            self.ext_viewmodel = ExamAddExternalViewModel()
            self.ext_view = ExamAddExternalView(self.ext_viewmodel, self.navigate_to_list, self.navigate_to_details)
            self.stacked_widget.addWidget(self.ext_view)
            self.stacked_widget.setCurrentWidget(self.ext_view)
        else:
            self.details_viewmodel = ExamDetailsViewModel(exam_id)
            self.details_view = ExamDetailsView(self.details_viewmodel, self.navigate_to_list)
            self.stacked_widget.addWidget(self.details_view)
            self.stacked_widget.setCurrentWidget(self.details_view)

    def navigate_to_take_exam(self, exam_id):
        self.take_viewmodel = ExamTakeViewModel(exam_id)
        self.take_view = ExamTakeView(self.take_viewmodel, self.navigate_to_list)
        self.stacked_widget.addWidget(self.take_view)
        self.stacked_widget.setCurrentWidget(self.take_view)
        
    def navigate_to_list(self):
        # Refresh list and switch back
        self.list_viewmodel.load_exams()
        self.stacked_widget.setCurrentWidget(self.list_view)
        
        # Optionally remove the details view
        widget = self.stacked_widget.widget(1)
        if widget:
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

    def setup_menu_bar(self):
        self.auth_action = QAction("Login / Register", self)
        self.auth_action.triggered.connect(self.show_auth_modal)
        self.ui.menu_main.insertAction(self.ui.action_settings, self.auth_action)
        self.ui.menu_main.insertSeparator(self.ui.action_settings)
        self.sync_action = QAction("Sync to Supabase", self)
        self.sync_action.triggered.connect(self.sync_viewmodel.sync_to_supabase)
        self.ui.menu_main.insertAction(self.ui.action_settings, self.sync_action)
        self.ui.menu_main.insertSeparator(self.ui.action_settings)
        self.logout_action = QAction("Logout", self)
        self.logout_action.triggered.connect(self.auth_viewmodel.sign_out)
        self.ui.menu_main.addSeparator()
        self.ui.menu_main.addAction(self.logout_action)
        self.ui.action_settings.triggered.connect(self.show_settings_modal)
        self._update_auth_actions()

    def _on_sync_started(self):
        self.sync_action.setEnabled(False)
        self.statusBar().showMessage("Syncing SQLite data to Supabase...")

    def _on_sync_finished(self, results):
        self.sync_action.setEnabled(True)
        summary = ", ".join(
            f"{result.table_name}: {result.row_count}" for result in results
        )
        self.statusBar().showMessage("Sync complete", 5000)
        QMessageBox.information(
            self,
            "Supabase Sync",
            f"SQLite data synced to Supabase.\n\n{summary}",
        )

    def _on_sync_failed(self, message):
        self.sync_action.setEnabled(True)
        self.statusBar().showMessage("Sync failed", 5000)
        QMessageBox.critical(
            self,
            "Supabase Sync Failed",
            message,
        )

    def show_settings_modal(self):
        minutes, ok = QInputDialog.getInt(self, "Settings", "Set time closeEvent (minutes):", self.close_event_minutes, 1, 1440, 1)
        if ok:
            self.close_event_minutes = minutes

    def show_auth_modal(self):
        if self.auth_dialog is not None and self.auth_dialog.isVisible():
            self.auth_dialog.raise_()
            self.auth_dialog.activateWindow()
            return

        self.auth_dialog = AuthView(self.auth_viewmodel, self)
        self.auth_dialog.finished.connect(self._on_auth_dialog_finished)
        self.auth_dialog.show()

    def _on_auth_dialog_finished(self):
        dialog = self.sender()
        if dialog is not None:
            dialog.deleteLater()
        self.auth_dialog = None

    def _on_authenticated(self, email):
        self.statusBar().showMessage(f"Signed in as {email}", 5000)
        self._update_auth_actions()

    def _on_logged_out(self):
        self.statusBar().showMessage("Signed out", 5000)
        self._update_auth_actions()

    def _update_auth_actions(self):
        is_loading = self.auth_viewmodel.is_loading
        is_signed_in = bool(self.auth_viewmodel.current_user_email)
        self.auth_action.setEnabled(not is_loading and not is_signed_in)
        self.logout_action.setEnabled(not is_loading and is_signed_in)

    def setup_mvvm_connections(self):
        """Bind ViewModel signals to View slots."""
        self.auth_viewmodel.state_changed.connect(self._update_auth_actions)
        self.auth_viewmodel.authenticated.connect(self._on_authenticated)
        self.auth_viewmodel.logged_out.connect(self._on_logged_out)
        self.reminder_viewmodel.show_study_window.connect(self.wakeup_and_focus_app)
        self.sync_viewmodel.sync_started.connect(self._on_sync_started)
        self.sync_viewmodel.sync_finished.connect(self._on_sync_finished)
        self.sync_viewmodel.sync_failed.connect(self._on_sync_failed)

    def setup_system_tray(self):
        """Configure background execution via System Tray."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(qta.icon('fa5s.graduation-cap', color='#1a73e8'))
        
        # Context Menu for Tray
        tray_menu = QMenu()
        open_action = QAction("Open Application", self)
        open_action.triggered.connect(self.showNormal)
        
        exit_action = QAction("Exit Completely", self)
        exit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(open_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Double click tray icon to restore
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def closeEvent(self, event):
        """Start the reminder timer when the user closes the app window."""
        if self.tray_icon.isVisible():
            # Ask whether to keep running in the background or exit completely.
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Jun Edu")
            msg_box.setText("What would you like to do?")
            msg_box.setInformativeText(
                f"Run in background: set a {self.close_event_minutes}-minute study reminder.\n"
                "Exit: close the application completely."
            )
            msg_box.setIcon(QMessageBox.Icon.Question)

            btn_tray = msg_box.addButton("Run in Background (System Tray)", QMessageBox.ButtonRole.AcceptRole)
            msg_box.addButton("Exit Completely", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(btn_tray)
            msg_box.exec()

            if msg_box.clickedButton() == btn_tray:
                minutes = self.close_event_minutes

                # Start the background countdown with the configured number of minutes.
                self.reminder_viewmodel.start_countdown(minutes)

                # Hide the main window.
                self.hide()

                # Show a system notification.
                self.tray_icon.showMessage(
                    "Jun Edu",
                    f"Set a {minutes}-minute reminder and continued running in the system tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

                # Prevent the application from exiting completely.
                event.ignore()
            else:
                # Exit completely.
                QApplication.quit()

    def wakeup_and_focus_app(self):
        """Force window into user focus and display study contents."""
        # 1. Trigger OS Notification
        self.tray_icon.showMessage(
            "TIME TO STUDY!",
            "Open your exercises now to keep the material fresh.",
            QSystemTrayIcon.MessageIcon.Warning,
            5000
        )
        
        # 2. Force Window Focus (Qt Native Window Management)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.showNormal()      
        self.raise_()           
        self.activateWindow()   
        
        # 3. Load Exam Content
        # self.stacked_widget.setCurrentWidget(self.list_view)

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
