from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer

from apps.icon_utils import make_theme_icon


class TitleBar(QFrame):
    """Custom frameless title bar with logo, title, theme toggle, and window controls."""

    minimize_requested = Signal()
    maximize_restore_requested = Signal()
    close_requested = Signal()
    sidebar_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._drag_pos = None
        self._dark_mode = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        # Sidebar toggle (hamburger)
        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setObjectName("titleBarBtn")
        self.sidebar_toggle_btn.setFixedSize(32, 32)
        self.sidebar_toggle_btn.setToolTip("Toggle Sidebar")
        self.sidebar_toggle_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        layout.addWidget(self.sidebar_toggle_btn)

        # Title
        self.title_label = QLabel("OSBoard")
        self.title_label.setObjectName("titleBarLabel")
        layout.addWidget(self.title_label)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Theme toggle
        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("titleBarBtn")
        self.theme_toggle_btn.setFixedSize(32, 32)
        self.theme_toggle_btn.setToolTip("Toggle Theme")
        layout.addWidget(self.theme_toggle_btn)

        # Window controls
        self.minimize_btn = self._make_window_btn("Minimize")
        self.minimize_btn.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self.minimize_btn)

        self.maximize_btn = self._make_window_btn("Maximize")
        self.maximize_btn.clicked.connect(self.maximize_restore_requested.emit)
        layout.addWidget(self.maximize_btn)

        self.close_btn = self._make_window_btn("Close")
        self.close_btn.setObjectName("titleBarCloseBtn")
        self.close_btn.clicked.connect(self.close_requested.emit)
        layout.addWidget(self.close_btn)

        self._apply_icons()

    def _make_window_btn(self, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("titleBarBtn")
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        return btn

    def _apply_icons(self) -> None:
        icons = {
            self.sidebar_toggle_btn: "icon_menu.png",
            self.theme_toggle_btn: (
                "cil-lightbulb.png" if self._dark_mode else "cil-moon.png"
            ),
            self.minimize_btn: "icon_minimize.png",
            self.close_btn: "icon_close.png",
        }
        for btn, name in icons.items():
            icon = make_theme_icon(name, self._dark_mode)
            if not icon.isNull():
                btn.setIcon(icon)

        self._apply_maximize_icon()

    def _apply_maximize_icon(self) -> None:
        icon = make_theme_icon("icon_maximize.png", self._dark_mode)
        if not icon.isNull():
            self.maximize_btn.setIcon(icon)

    def set_maximized_state(self, maximized: bool) -> None:
        icon_name = "icon_restore.png" if maximized else "icon_maximize.png"
        icon = make_theme_icon(icon_name, self._dark_mode)
        if not icon.isNull():
            self.maximize_btn.setIcon(icon)
        self.maximize_btn.setToolTip("Restore" if maximized else "Maximize")

    def set_theme(self, is_dark: bool) -> None:
        self._dark_mode = is_dark
        self._apply_icons()
        self.theme_toggle_btn.setToolTip(
            "Switch to Light Theme" if is_dark else "Switch to Dark Theme"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            window = self.window()
            if window.isMaximized():
                window.showNormal()
                self.set_maximized_state(False)
            delta = event.globalPosition().toPoint() - self._drag_pos
            window.move(window.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            QTimer.singleShot(200, self.maximize_restore_requested.emit)
