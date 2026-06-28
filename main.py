import os
import sys

from PySide6.QtWidgets import QApplication
from src.repositories.sqlite.database import init_db

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.views.main_window import MainWindow

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
