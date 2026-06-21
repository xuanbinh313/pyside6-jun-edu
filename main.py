import sys
import os
from PySide6.QtWidgets import QApplication

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.database import init_db
from src.views.main_window import MainWindow


if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
