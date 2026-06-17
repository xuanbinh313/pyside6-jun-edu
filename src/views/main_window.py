import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
import qtawesome as qta

# Add current directory to path if needed, but normally running from jun-edu is fine.
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.views.exam_list_view import ExamListView
from src.views.exam_details_view import ExamDetailsView
from src.views.exam_add_external_view import ExamAddExternalView
from src.viewmodels.exam_list_viewmodel import ExamListViewModel
from src.viewmodels.exam_details_viewmodel import ExamDetailsViewModel
from src.viewmodels.exam_add_external_viewmodel import ExamAddExternalViewModel
from src.viewmodels.reminder_viewmodel import ReminderViewModel
from src.models.database import init_db

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jun Edu - Exam Management")
        self.resize(1000, 700)
        
        self.reminder_viewmodel = ReminderViewModel()
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.list_viewmodel = ExamListViewModel()
        self.list_view = ExamListView(self.list_viewmodel, self.navigate_to_details)
        
        self.stacked_widget.addWidget(self.list_view)
        
        self.close_event_minutes = 1
        self.setup_menu_bar()
        
        self.setup_system_tray()
        self.setup_mvvm_connections()
        
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
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("Menu")
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_modal)
        settings_menu.addAction(settings_action)

    def show_settings_modal(self):
        minutes, ok = QInputDialog.getInt(self, "Settings", "Set time closeEvent (minutes):", self.close_event_minutes, 1, 1440, 1)
        if ok:
            self.close_event_minutes = minutes

    def setup_mvvm_connections(self):
        """Bind ViewModel signals to View slots."""
        self.reminder_viewmodel.show_study_window.connect(self.wakeup_and_focus_app)

    def setup_system_tray(self):
        """Configure background execution via System Tray."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(qta.icon('fa5s.graduation-cap', color='#1a73e8'))
        
        # Context Menu for Tray
        tray_menu = QMenu()
        open_action = QAction("Mở ứng dụng", self)
        open_action.triggered.connect(self.showNormal)
        
        exit_action = QAction("Thoát hoàn toàn", self)
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
        """Kích hoạt bộ đếm giờ ngay khi user bấm nút X thoát app"""
        if self.tray_icon.isVisible():
            minutes = self.close_event_minutes
            
            # 2. Ra lệnh cho bộ não bắt đầu đếm ngược ngầm với số phút tìm được
            self.reminder_viewmodel.start_countdown(minutes)
            
            # 3. Ẩn cửa sổ chính đi
            self.hide()
            
            # 4. Bắn thông báo hệ thống
            self.tray_icon.showMessage(
                "Jun Edu",
                f"Đã tự động hẹn giờ {minutes} phút và chạy ngầm dưới khay hệ thống!",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            
            # 5. Ngăn không cho ứng dụng bị tắt hoàn toàn
            event.ignore()

    def wakeup_and_focus_app(self):
        """Force window into user focus and display study contents."""
        # 1. Trigger OS Notification
        self.tray_icon.showMessage(
            "ĐẾN GIỜ HỌC RỒI!",
            "Hãy vào làm bài tập ngay để không bị quên kiến thức nhé.",
            QSystemTrayIcon.MessageIcon.Warning,
            5000
        )
        
        # 2. Force Window Focus (Qt Native Window Management)
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
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
