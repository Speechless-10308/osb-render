from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QFrame,
    QScrollArea,
    QScroller,
)
from PySide6.QtGui import QTextCursor, QColor, QIcon
from PySide6.QtCore import Signal, Qt, QSize

from apps.icon_utils import icon_path, make_theme_icon, make_muted_icon, load_and_tint

_WHITE = QColor("#FFFFFF")


def _white_icon(name: str) -> QIcon:
    icon = load_and_tint(name, _WHITE)
    if not icon.isNull():
        return icon
    return QIcon(icon_path(name))


class HomePage(QWidget):
    """Main rendering page with card-based layout and always-visible console."""

    start_requested = Signal()
    stop_requested = Signal()
    browse_osu_requested = Signal()
    browse_output_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = True

        # Outer layout holds the scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area — prevents element overlap on short windows
        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        inner = QWidget()
        inner.setObjectName("homeInner")

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ============================================================
        # Card 1: File Source
        # ============================================================
        file_card = QFrame()
        file_card.setObjectName("card")
        file_card_layout = QVBoxLayout(file_card)
        file_card_layout.setContentsMargins(20, 16, 20, 16)
        file_card_layout.setSpacing(10)

        file_title = QLabel("File Source")
        file_title.setObjectName("cardTitle")
        file_card_layout.addWidget(file_title)

        # .osu file row
        osu_row = QHBoxLayout()
        osu_row.setContentsMargins(0, 0, 0, 0)
        osu_row.setSpacing(10)

        self.osu_icon = QLabel()
        self.osu_icon.setObjectName("cardIcon")
        self.osu_icon.setFixedSize(24, 24)
        osu_row.addWidget(self.osu_icon)

        self.osu_path_edit = QLineEdit()
        self.osu_path_edit.setObjectName("filePathInput")
        self.osu_path_edit.setPlaceholderText("Select .osu file...")
        osu_row.addWidget(self.osu_path_edit, stretch=1)

        self.browse_osu_btn = QPushButton("Browse")
        self.browse_osu_btn.setObjectName("browseBtn")
        self.browse_osu_btn.clicked.connect(self.browse_osu_requested.emit)
        osu_row.addWidget(self.browse_osu_btn)
        file_card_layout.addLayout(osu_row)

        # Output .mp4 row
        out_row = QHBoxLayout()
        out_row.setContentsMargins(0, 0, 0, 0)
        out_row.setSpacing(10)

        self.out_icon = QLabel()
        self.out_icon.setObjectName("cardIcon")
        self.out_icon.setFixedSize(24, 24)
        out_row.addWidget(self.out_icon)

        self.out_path_edit = QLineEdit()
        self.out_path_edit.setObjectName("filePathInput")
        self.out_path_edit.setPlaceholderText("Output .mp4 path...")
        out_row.addWidget(self.out_path_edit, stretch=1)

        self.browse_out_btn = QPushButton("Save As")
        self.browse_out_btn.setObjectName("browseBtn")
        self.browse_out_btn.clicked.connect(self.browse_output_requested.emit)
        out_row.addWidget(self.browse_out_btn)
        file_card_layout.addLayout(out_row)
        layout.addWidget(file_card)

        # ============================================================
        # Card 2: Parameters — Grouped Dual-Column Form
        # ============================================================
        params_card = QFrame()
        params_card.setObjectName("card")
        params_layout = QVBoxLayout(params_card)
        params_layout.setContentsMargins(20, 16, 20, 16)
        params_layout.setSpacing(10)

        params_title = QLabel("Parameters")
        params_title.setObjectName("cardTitle")
        params_layout.addWidget(params_title)

        # Horizontal layout: two bordered group frames
        groups_row = QHBoxLayout()
        groups_row.setContentsMargins(0, 0, 0, 0)
        groups_row.setSpacing(16)

        # --- Left group: Visual Settings ---
        visual_frame = QFrame()
        visual_frame.setObjectName("settingGroup")
        visual_layout = QGridLayout(visual_frame)
        visual_layout.setContentsMargins(14, 10, 14, 10)
        visual_layout.setHorizontalSpacing(8)
        visual_layout.setVerticalSpacing(8)

        vis_header = QLabel("Visual Settings")
        vis_header.setObjectName("groupHeader")
        visual_layout.addWidget(vis_header, 0, 0, 1, 2)

        w_label = QLabel("Width")
        w_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        w_label.setFixedWidth(55)
        visual_layout.addWidget(w_label, 1, 0)

        self.width_spin = QSpinBox()
        self.width_spin.setObjectName("resSpinBox")
        self.width_spin.setRange(100, 7680)
        self.width_spin.setValue(1920)
        self.width_spin.setFixedWidth(110)
        self.width_spin.setMinimumHeight(30)
        self.width_spin.setAlignment(Qt.AlignCenter)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        visual_layout.addWidget(self.width_spin, 1, 1)

        h_label = QLabel("Height")
        h_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h_label.setFixedWidth(55)
        visual_layout.addWidget(h_label, 2, 0)

        height_row = QHBoxLayout()
        height_row.setContentsMargins(0, 0, 0, 0)
        height_row.setSpacing(4)

        self.height_spin = QSpinBox()
        self.height_spin.setObjectName("resSpinBox")
        self.height_spin.setRange(100, 4320)
        self.height_spin.setValue(1080)
        self.height_spin.setFixedWidth(110)
        self.height_spin.setMinimumHeight(30)
        self.height_spin.setAlignment(Qt.AlignCenter)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        height_row.addWidget(self.height_spin)

        self.link_btn = QPushButton()
        self.link_btn.setObjectName("linkBtn")
        self.link_btn.setCheckable(True)
        self.link_btn.setChecked(True)
        self.link_btn.setFixedSize(20, 24)
        self.link_btn.setIconSize(QSize(16, 16))
        self.link_btn.setToolTip("Lock Aspect Ratio")
        self.link_btn.setCursor(Qt.PointingHandCursor)
        self.link_btn.toggled.connect(self._on_link_toggled)
        height_row.addWidget(self.link_btn)
        height_row.addStretch()

        visual_layout.addLayout(height_row, 2, 1)

        fps_label = QLabel("FPS")
        fps_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fps_label.setFixedWidth(55)
        visual_layout.addWidget(fps_label, 3, 0)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 999)
        self.fps_spin.setValue(60)
        self.fps_spin.setFixedWidth(110)
        self.fps_spin.setMinimumHeight(30)
        self.fps_spin.setAlignment(Qt.AlignCenter)
        visual_layout.addWidget(self.fps_spin, 3, 1)

        groups_row.addWidget(visual_frame, stretch=1)

        # --- Right group: Encoding Settings ---
        encode_frame = QFrame()
        encode_frame.setObjectName("settingGroup")
        encode_layout = QGridLayout(encode_frame)
        encode_layout.setContentsMargins(14, 10, 14, 10)
        encode_layout.setHorizontalSpacing(8)
        encode_layout.setVerticalSpacing(8)

        enc_header = QLabel("Encoding Settings")
        enc_header.setObjectName("groupHeader")
        encode_layout.addWidget(enc_header, 0, 0, 1, 2)

        self.gpu_checkbox = QCheckBox("Use GPU Acceleration")
        self.gpu_checkbox.setChecked(True)
        encode_layout.addWidget(self.gpu_checkbox, 1, 0, 1, 2)

        preset_label = QLabel("Preset")
        preset_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        preset_label.setFixedWidth(55)
        encode_layout.addWidget(preset_label, 2, 0)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow",
        ])
        self.preset_combo.setCurrentIndex(5)
        self.preset_combo.setFixedWidth(140)
        encode_layout.addWidget(self.preset_combo, 2, 1)

        crf_label = QLabel("CRF")
        crf_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        crf_label.setFixedWidth(55)
        encode_layout.addWidget(crf_label, 3, 0)

        self.crf_spin = QSpinBox()
        self.crf_spin.setObjectName("crfSpin")
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(20)
        self.crf_spin.setFixedWidth(140)
        self.crf_spin.setMinimumHeight(30)
        self.crf_spin.setToolTip("0 lossless, 23 default, 51 worst.")
        self.crf_spin.setAlignment(Qt.AlignCenter)
        encode_layout.addWidget(self.crf_spin, 3, 1)

        groups_row.addWidget(encode_frame, stretch=1)

        params_layout.addLayout(groups_row)
        layout.addWidget(params_card)

        # Aspect ratio state
        self._aspect_ratio = 1920.0 / 1080.0
        self._link_locked = True

        # ============================================================
        # Action Buttons
        # ============================================================
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(12)

        self.start_btn = QPushButton("Start Rendering")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_requested.emit)
        action_row.addWidget(self.start_btn, stretch=2)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("secondaryBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        action_row.addWidget(self.stop_btn, stretch=1)

        layout.addLayout(action_row)

        # ============================================================
        # Card 3: Execution Monitor
        # ============================================================
        monitor_card = QFrame()
        monitor_card.setObjectName("card")
        monitor_layout = QVBoxLayout(monitor_card)
        monitor_layout.setContentsMargins(20, 16, 20, 20)
        monitor_layout.setSpacing(10)

        monitor_title = QLabel("Execution Monitor")
        monitor_title.setObjectName("cardTitle")
        monitor_layout.addWidget(monitor_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% (%v/%m frames)")
        monitor_layout.addWidget(self.progress_bar)

        self.console_log = QTextEdit()
        self.console_log.setObjectName("consoleOutput")
        self.console_log.setReadOnly(True)
        self.console_log.setMinimumHeight(120)
        monitor_layout.addWidget(self.console_log, stretch=1)

        layout.addWidget(monitor_card)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Track input widgets for enable/disable during rendering
        self._input_widgets = [
            self.osu_path_edit,
            self.out_path_edit,
            self.browse_osu_btn,
            self.browse_out_btn,
            self.width_spin,
            self.height_spin,
            self.link_btn,
            self.fps_spin,
            self.gpu_checkbox,
            self.preset_combo,
            self.crf_spin,
        ]

        # Apply initial icons
        self._apply_icons()

    # --- Aspect Ratio Logic ---
    def _on_link_toggled(self, checked: bool) -> None:
        self._link_locked = checked
        if checked:
            h = self.height_spin.value()
            if h > 0:
                self._aspect_ratio = self.width_spin.value() / h
        self._apply_link_icon()

    def _on_width_changed(self, value: int) -> None:
        if self._link_locked:
            new_height = round(value / self._aspect_ratio)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(new_height)
            self.height_spin.blockSignals(False)

    def _on_height_changed(self, value: int) -> None:
        if self._link_locked:
            new_width = round(value * self._aspect_ratio)
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(new_width)
            self.width_spin.blockSignals(False)

    # --- Icon helpers ---
    def _apply_icons(self) -> None:
        # Card decorative icons (muted, theme-aware)
        for label, name in [
            (self.osu_icon, "file.svg"),
            (self.out_icon, "File save.svg"),
        ]:
            icon = make_muted_icon(name, self._dark_mode)
            if not icon.isNull():
                label.setPixmap(icon.pixmap(24, 24))

        # Browse / Save As button icons (theme foreground)
        for btn, name in [
            (self.browse_osu_btn, "file.svg"),
            (self.browse_out_btn, "File save.svg"),
        ]:
            icon = make_theme_icon(name, self._dark_mode)
            if not icon.isNull():
                btn.setIcon(icon)

        # Start / Stop — always white (visible on pink/red buttons)
        self.start_btn.setIcon(_white_icon("debug-start.svg"))
        self.stop_btn.setIcon(_white_icon("stop.svg"))

        self._apply_link_icon()

    def _apply_link_icon(self) -> None:
        icon = make_theme_icon("cil-link.png", self._dark_mode)
        if not icon.isNull():
            self.link_btn.setIcon(icon)

    def set_theme_icons(self, is_dark: bool) -> None:
        self._dark_mode = is_dark
        self._apply_icons()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_file_paths(self) -> tuple[str, str]:
        return self.osu_path_edit.text(), self.out_path_edit.text()

    def set_file_paths(self, osu_path: str, output_path: str) -> None:
        self.osu_path_edit.setText(osu_path)
        self.out_path_edit.setText(output_path)

    def set_osu_path(self, path: str) -> None:
        self.osu_path_edit.setText(path)

    def set_output_path(self, path: str) -> None:
        self.out_path_edit.setText(path)

    def get_render_params(self) -> dict:
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "fps": self.fps_spin.value(),
            "use_gpu": self.gpu_checkbox.isChecked(),
            "encoder_preset": self.preset_combo.currentText(),
            "crf": self.crf_spin.value(),
        }

    def set_render_params(self, width: int, height: int, fps: int, use_gpu: bool,
                          encoder_preset: str = "fast", crf: int = 20) -> None:
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self._aspect_ratio = width / max(height, 1)
        self.fps_spin.setValue(fps)
        self.gpu_checkbox.setChecked(use_gpu)
        idx = self.preset_combo.findText(encoder_preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.crf_spin.setValue(crf)

    def set_rendering_state(self, running: bool) -> None:
        for w in self._input_widgets:
            w.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def append_log(self, message: str, level: str) -> None:
        color_map = {
            "ERROR": "#ff5555",
            "WARNING": "#ffb86c",
            "INFO": "#50fa7b",
        }
        color = color_map.get(level, "#f8f8f2")
        formatted = f'<span style="color:{color}">[{level}]</span> {message}'
        self.console_log.append(formatted)
        self.console_log.moveCursor(QTextCursor.End)

    def clear_log(self) -> None:
        self.console_log.clear()
