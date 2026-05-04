import os

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Signal, Qt

from apps.icon_utils import icon_path, make_muted_icon, get_project_root


class Sidebar(QFrame):
    """Collapsible left navigation sidebar with logo and icon+text buttons."""

    page_changed = Signal(int)
    toggled = Signal(bool)

    SIDEBAR_EXPANDED = 220
    SIDEBAR_COLLAPSED = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self._expanded = True
        self.setFixedWidth(self.SIDEBAR_EXPANDED)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 8)
        layout.setSpacing(0)

        # --- Brand row: logo + name, horizontal ---
        self._brand_row = QHBoxLayout()
        self._brand_row.setContentsMargins(20, 8, 8, 8)
        self._brand_row.setSpacing(8)

        # Logo icon — always visible
        self.logo_icon = QLabel()
        self.logo_icon.setObjectName("sidebarIcon")
        self.logo_icon.setFixedSize(40, 40)
        logo_path = os.path.join(get_project_root(), "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                pix = pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_icon.setPixmap(pix)
        self._brand_row.addWidget(self.logo_icon)

        # Brand name — hidden when collapsed
        self.brand_label = QLabel("OSBoard")
        self.brand_label.setObjectName("sidebarBrand")
        self._brand_row.addWidget(self.brand_label)
        self._brand_row.addStretch()

        layout.addLayout(self._brand_row)

        layout.addSpacing(8)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Navigation buttons with icons
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        self.home_btn = self._create_nav_button("Home", "cil-home.png", 0)
        self.settings_btn = self._create_nav_button("Settings", "cil-settings.png", 1)
        self.about_btn = self._create_nav_button("About", "cil-description.png", 2)

        layout.addWidget(self.home_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.about_btn)

        # Spacer pushes everything up
        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.home_btn.setChecked(True)
        self._btn_group.idClicked.connect(self.page_changed.emit)

    def _create_nav_button(self, text: str, icon_name: str, page_id: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("sidebarBtn")
        btn.setCheckable(True)

        p = icon_path(icon_name)
        if os.path.exists(p):
            btn.setIcon(QIcon(p))

        self._btn_group.addButton(btn, page_id)
        return btn

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self.setProperty("collapsed", not self._expanded)

        # Adjust brand row margins: centered logo when collapsed
        if self._expanded:
            self._brand_row.setContentsMargins(20, 8, 8, 8)
        else:
            self._brand_row.setContentsMargins(10, 8, 10, 8)

        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.emit(self._expanded)

    def set_theme_icons(self, is_dark: bool) -> None:
        icon_map = {
            self.home_btn: "cil-home.png",
            self.settings_btn: "cil-settings.png",
            self.about_btn: "cil-description.png",
        }
        for btn, name in icon_map.items():
            icon = make_muted_icon(name, is_dark)
            if not icon.isNull():
                btn.setIcon(icon)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_active_page(self, index: int) -> None:
        btn = self._btn_group.button(index)
        if btn is not None:
            self._btn_group.blockSignals(True)
            btn.setChecked(True)
            self._btn_group.blockSignals(False)

    def expanded_width(self) -> int:
        return self.SIDEBAR_EXPANDED

    def collapsed_width(self) -> int:
        return self.SIDEBAR_COLLAPSED
