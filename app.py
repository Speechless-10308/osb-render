import sys
import os
import multiprocessing


from PySide6.QtWidgets import QApplication

from apps.main_window import MainWindow
from src.config import Config
from src.jobs import RenderJob


if __name__ == "__main__":
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
