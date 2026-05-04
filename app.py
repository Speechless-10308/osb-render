import sys
import os
import multiprocessing

from PySide6.QtWidgets import QApplication

from apps.main_window import MainWindow


def _get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _load_theme(app: QApplication, theme: str = "dark") -> None:
    qss_path = os.path.join(_get_app_dir(), "themes", f"osboard_{theme}.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


if __name__ == "__main__":
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _load_theme(app, "dark")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
