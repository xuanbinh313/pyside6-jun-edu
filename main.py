import os
import sys

from PySide6.QtWidgets import QApplication
from src.repositories.sqlite.database import init_db

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.views.main_window import MainWindow, create_startup_splash

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    splash = create_startup_splash()
    splash.show()
    app.processEvents()
    widget = MainWindow(splash=splash)
    widget.show()
    splash.finish(widget)
    sys.exit(app.exec())
