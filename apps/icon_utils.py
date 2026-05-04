"""Shared icon loading utilities with theme-aware tinting."""
import os
import sys

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt


def get_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_icon_dir() -> str:
    return os.path.join(get_project_root(), "icons")


def icon_path(name: str) -> str:
    return os.path.join(get_icon_dir(), name)


def load_and_tint(name: str, target_color: QColor) -> QIcon:
    """Load any icon (PNG/SVG) and tint all non-transparent pixels."""
    path = icon_path(name)
    if not os.path.exists(path):
        return QIcon()

    pixmap = QPixmap(path)
    if pixmap.isNull():
        return QIcon()

    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), target_color)
    painter.end()
    return QIcon(tinted)


def make_theme_icon(name: str, dark_mode: bool) -> QIcon:
    """Tint icon to foreground color for the current theme."""
    color = QColor("#f8f8f2") if dark_mode else QColor("#2E354F")
    return load_and_tint(name, color)


def make_muted_icon(name: str, dark_mode: bool) -> QIcon:
    """Tint icon to muted/sidebar accent color for the current theme."""
    color = QColor("#6272a4") if dark_mode else QColor("#7C829A")
    return load_and_tint(name, color)
