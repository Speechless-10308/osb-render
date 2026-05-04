import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from apps.icon_utils import get_project_root


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 24, 48, 24)
        layout.setSpacing(12)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)

        logo_path = os.path.join(get_project_root(), "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_label.setPixmap(pixmap)

        layout.addWidget(logo_label)

        # Project name
        title = QLabel("OSBoard")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel("v0.1.0")
        version.setObjectName("aboutDescription")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        # Description
        desc = QLabel(
            "A high-performance osu! storyboard renderer.\n"
            "Convert your beatmap storyboards into smooth MP4 videos\n"
            "with GPU-accelerated rendering via Skia."
        )
        desc.setObjectName("aboutDescription")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(16)

        # Credits
        credits = QLabel("Built with PySide6 + Skia + FFmpeg")
        credits.setObjectName("mutedLabel")
        credits.setAlignment(Qt.AlignCenter)
        layout.addWidget(credits)

        license_label = QLabel("MIT License")
        license_label.setObjectName("mutedLabel")
        license_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_label)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
