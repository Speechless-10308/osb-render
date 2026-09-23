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
    QComboBox,
    QFrame,
    QScrollArea,
    QScroller,
)
from PySide6.QtGui import QTextCursor, QColor, QIcon
from PySide6.QtCore import Signal, Qt, QSize

from apps.icon_utils import icon_path, make_theme_icon, load_and_tint
from apps.widgets import ToggleSwitch

_WHITE = QColor("#FFFFFF")


def _white_icon(name: str) -> QIcon:
    icon = load_and_tint(name, _WHITE)
    if not icon.isNull():
        return icon
    return QIcon(icon_path(name))


class HomePage(QWidget):
    """Main storyboard rendering page."""

    start_requested = Signal()
    stop_requested = Signal()
    browse_osu_requested = Signal()
    browse_output_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = True
        self._aspect_ratio = 1920.0 / 1080.0
        self._link_locked = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        inner = QWidget()
        inner.setObjectName("homeInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(26, 24, 26, 26)
        layout.setSpacing(14)

        title = QLabel("Render storyboard")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QLabel("Convert an osu! storyboard into a production-ready video.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        file_card = QFrame()
        file_card.setObjectName("card")
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(20, 16, 20, 18)
        file_layout.setSpacing(10)
        file_title = QLabel("Input & output")
        file_title.setObjectName("cardTitle")
        file_layout.addWidget(file_title)

        self.osu_icon, self.osu_path_edit, self.browse_osu_btn = self._make_path_row(
            "Beatmap file", "Select .osu file...", "folder-open.svg", "Browse"
        )
        self.browse_osu_btn.clicked.connect(self.browse_osu_requested.emit)
        file_layout.addLayout(self._path_layout(
            "Beatmap file", self.osu_icon, self.osu_path_edit, self.browse_osu_btn
        ))

        self.out_icon, self.out_path_edit, self.browse_out_btn = self._make_path_row(
            "Output video", "Output .mp4 path...", "save-file.svg", "Save as"
        )
        self.browse_out_btn.clicked.connect(self.browse_output_requested.emit)
        file_layout.addLayout(self._path_layout(
            "Output video", self.out_icon, self.out_path_edit, self.browse_out_btn
        ))
        layout.addWidget(file_card)

        params_card = QFrame()
        params_card.setObjectName("card")
        params_layout = QVBoxLayout(params_card)
        params_layout.setContentsMargins(20, 16, 20, 18)
        params_layout.setSpacing(12)
        params_title = QLabel("Render settings")
        params_title.setObjectName("cardTitle")
        params_layout.addWidget(params_title)

        groups_row = QHBoxLayout()
        groups_row.setContentsMargins(0, 0, 0, 0)
        groups_row.setSpacing(18)

        visual_frame = QFrame()
        visual_frame.setObjectName("settingGroup")
        visual_layout = QGridLayout(visual_frame)
        visual_layout.setContentsMargins(14, 10, 14, 12)
        visual_layout.setHorizontalSpacing(8)
        visual_layout.setVerticalSpacing(8)
        visual_layout.setColumnStretch(1, 1)
        vis_header = QLabel("Output")
        vis_header.setObjectName("groupHeader")
        visual_layout.addWidget(vis_header, 0, 0, 1, 2)
        visual_layout.addWidget(self._label("Resolution"), 1, 0)

        resolution_row = QHBoxLayout()
        resolution_row.setContentsMargins(0, 0, 0, 0)
        resolution_row.setSpacing(5)
        self.width_spin = self._make_spin(100, 7680, 1920, "resSpinBox")
        self.height_spin = self._make_spin(100, 4320, 1080, "resSpinBox")
        self.width_spin.valueChanged.connect(self._on_width_changed)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        resolution_row.addWidget(self.width_spin)
        resolution_row.addWidget(self._label("×", "dimensionSeparator"))
        resolution_row.addWidget(self.height_spin)
        self.link_btn = QPushButton()
        self.link_btn.setObjectName("linkBtn")
        self.link_btn.setCheckable(True)
        self.link_btn.setChecked(True)
        self.link_btn.setFixedSize(28, 30)
        self.link_btn.setIconSize(QSize(16, 16))
        self.link_btn.setToolTip("Lock aspect ratio")
        self.link_btn.setCursor(Qt.PointingHandCursor)
        self.link_btn.toggled.connect(self._on_link_toggled)
        resolution_row.addWidget(self.link_btn)
        visual_layout.addLayout(resolution_row, 1, 1)

        visual_layout.addWidget(self._label("Frame rate"), 2, 0)
        self.fps_spin = self._make_spin(1, 999, 60, "fpsSpin")
        self.fps_spin.setSuffix(" FPS")
        self.fps_spin.valueChanged.connect(self._update_summary)
        visual_layout.addWidget(self.fps_spin, 2, 1)
        groups_row.addWidget(visual_frame, 1)

        performance_frame = QFrame()
        performance_frame.setObjectName("settingGroup")
        performance_layout = QGridLayout(performance_frame)
        performance_layout.setContentsMargins(14, 10, 14, 12)
        performance_layout.setHorizontalSpacing(8)
        performance_layout.setVerticalSpacing(8)
        performance_layout.setColumnStretch(1, 1)
        perf_header = QLabel("Performance")
        perf_header.setObjectName("groupHeader")
        performance_layout.addWidget(perf_header, 0, 0, 1, 2)
        self.gpu_checkbox = ToggleSwitch("Use GPU acceleration")
        self.gpu_checkbox.setObjectName("gpuToggle")
        self.gpu_checkbox.setChecked(True)
        self.gpu_checkbox.toggled.connect(self._update_summary)
        performance_layout.addWidget(self.gpu_checkbox, 1, 0, 1, 2)
        performance_layout.addWidget(self._label("Backend"), 2, 0)
        self.backend_value = QLineEdit("Skia / OpenGL")
        self.backend_value.setObjectName("readOnlyValue")
        self.backend_value.setReadOnly(True)
        self.backend_value.setFocusPolicy(Qt.NoFocus)
        performance_layout.addWidget(self.backend_value, 2, 1)
        groups_row.addWidget(performance_frame, 1)

        encode_frame = QFrame()
        encode_frame.setObjectName("settingGroup")
        encode_layout = QGridLayout(encode_frame)
        encode_layout.setContentsMargins(14, 10, 14, 12)
        encode_layout.setHorizontalSpacing(8)
        encode_layout.setVerticalSpacing(8)
        encode_layout.setColumnStretch(1, 1)
        enc_header = QLabel("Quality")
        enc_header.setObjectName("groupHeader")
        encode_layout.addWidget(enc_header, 0, 0, 1, 2)
        encode_layout.addWidget(self._label("Preset"), 1, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow",
        ])
        self.preset_combo.setCurrentIndex(4)
        encode_layout.addWidget(self.preset_combo, 1, 1)
        encode_layout.addWidget(self._label("CRF"), 2, 0)
        self.crf_spin = self._make_spin(0, 51, 20, "crfSpin")
        self.crf_spin.setToolTip("0 is lossless, 23 is default, 51 is worst.")
        encode_layout.addWidget(self.crf_spin, 2, 1)
        groups_row.addWidget(encode_frame, 1)
        params_layout.addLayout(groups_row)
        layout.addWidget(params_card)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(12)
        self.summary_strip = QFrame()
        self.summary_strip.setObjectName("summaryStrip")
        summary_layout = QHBoxLayout(self.summary_strip)
        summary_layout.setContentsMargins(14, 0, 14, 0)
        summary_layout.setSpacing(8)
        self.summary_icon = QLabel()
        self.summary_icon.setObjectName("summaryIcon")
        self.summary_icon.setFixedSize(20, 20)
        summary_layout.addWidget(self.summary_icon)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summaryLabel")
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch()
        action_row.addWidget(self.summary_strip, 1)

        self.start_btn = QPushButton("Render video")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_requested.emit)
        action_row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("secondaryBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        action_row.addWidget(self.stop_btn)
        layout.addLayout(action_row)

        monitor_card = QFrame()
        monitor_card.setObjectName("card")
        monitor_layout = QVBoxLayout(monitor_card)
        monitor_layout.setContentsMargins(20, 16, 20, 20)
        monitor_layout.setSpacing(10)
        monitor_header = QHBoxLayout()
        monitor_title = QLabel("Rendering status")
        monitor_title.setObjectName("cardTitle")
        monitor_header.addWidget(monitor_title)
        monitor_header.addStretch()
        self.console_toggle_btn = QPushButton("Hide details")
        self.console_toggle_btn.setObjectName("textBtn")
        self.console_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.console_toggle_btn.clicked.connect(self._toggle_console)
        monitor_header.addWidget(self.console_toggle_btn)
        monitor_layout.addLayout(monitor_header)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready to render")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("state", "ready")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.progress_meta = QLabel("0%  ·  0 / 0 frames")
        self.progress_meta.setObjectName("progressMeta")
        status_row.addWidget(self.progress_meta)
        monitor_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("renderProgress")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        monitor_layout.addWidget(self.progress_bar)
        self.console_log = QTextEdit()
        self.console_log.setObjectName("consoleOutput")
        self.console_log.setReadOnly(True)
        self.console_log.setMinimumHeight(112)
        monitor_layout.addWidget(self.console_log)
        layout.addWidget(monitor_card)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self._input_widgets = [
            self.osu_path_edit, self.out_path_edit, self.browse_osu_btn,
            self.browse_out_btn, self.width_spin, self.height_spin,
            self.link_btn, self.fps_spin, self.gpu_checkbox,
            self.preset_combo, self.crf_spin,
        ]
        self._apply_icons()
        self._update_summary()

    @staticmethod
    def _label(text: str, object_name: str = "fieldLabel") -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    @staticmethod
    def _make_spin(minimum: int, maximum: int, value: int,
                   object_name: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setMinimumHeight(30)
        spin.setAlignment(Qt.AlignCenter)
        return spin

    @staticmethod
    def _make_path_row(label_text: str, placeholder: str,
                       icon_name: str, button_text: str):
        icon = QLabel()
        icon.setObjectName("cardIcon")
        icon.setFixedSize(22, 22)
        edit = QLineEdit()
        edit.setObjectName("filePathInput")
        edit.setPlaceholderText(placeholder)
        button = QPushButton(button_text)
        button.setObjectName("browseBtn")
        button.setProperty("iconName", icon_name)
        edit.setToolTip(label_text)
        return icon, edit, button

    @staticmethod
    def _path_layout(label_text: str, icon, edit, button) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel(label_text)
        label.setObjectName("pathFieldLabel")
        layout.addWidget(label)
        layout.addWidget(icon)
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return layout

    # --- Aspect ratio logic ---
    def _on_link_toggled(self, checked: bool) -> None:
        self._link_locked = checked
        if checked and self.height_spin.value() > 0:
            self._aspect_ratio = self.width_spin.value() / self.height_spin.value()

    def _on_width_changed(self, value: int) -> None:
        if self._link_locked:
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(round(value / self._aspect_ratio))
            self.height_spin.blockSignals(False)
        self._update_summary()

    def _on_height_changed(self, value: int) -> None:
        if self._link_locked:
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(round(value * self._aspect_ratio))
            self.width_spin.blockSignals(False)
        self._update_summary()

    def _update_summary(self, *args) -> None:
        if not hasattr(self, "summary_label"):
            return
        backend = "GPU" if self.gpu_checkbox.isChecked() else "CPU"
        self.summary_label.setText(
            f"{self.width_spin.value()} × {self.height_spin.value()}  ·  "
            f"{self.fps_spin.value()} FPS  ·  H.264  ·  {backend}"
        )

    def _apply_icons(self) -> None:
        for label, name in [
            (self.osu_icon, "file-beatmap.svg"),
            (self.out_icon, "file-output.svg"),
        ]:
            icon = make_theme_icon(name, self._dark_mode)
            if not icon.isNull():
                label.setPixmap(icon.pixmap(22, 22))
        for button in (self.browse_osu_btn, self.browse_out_btn):
            icon = make_theme_icon(button.property("iconName"), self._dark_mode)
            if not icon.isNull():
                button.setIcon(icon)
        self.start_btn.setIcon(_white_icon("play.svg"))
        self.stop_btn.setIcon(_white_icon("stop-square.svg"))
        icon = make_theme_icon("link.svg", self._dark_mode)
        if not icon.isNull():
            self.link_btn.setIcon(icon)
        icon = make_theme_icon("video-summary.svg", self._dark_mode)
        if not icon.isNull():
            self.summary_icon.setPixmap(icon.pixmap(20, 20))

    def set_theme_icons(self, is_dark: bool) -> None:
        self._dark_mode = is_dark
        self.gpu_checkbox.set_theme(is_dark)
        self._apply_icons()

    # --- Public API ---
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
        self._update_summary()

    def set_rendering_state(self, running: bool) -> None:
        for widget in self._input_widgets:
            widget.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        if running:
            self._set_status("Rendering…", "running")
        elif self.status_label.property("state") == "running":
            self._set_status("Ready to render", "ready")

    def update_progress(self, current: int, total: int) -> None:
        total = max(total, 1)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        percent = round(current * 100 / total)
        self.progress_meta.setText(f"{percent}%  ·  {current:,} / {total:,} frames")

    def append_log(self, message: str, level: str) -> None:
        color_map = {
            "ERROR": "#ff6b7a",
            "WARNING": "#f4b860",
            "INFO": "#58c98b",
        }
        color = color_map.get(level, "#f2f4f7")
        formatted = f'<span style="color:{color}">[{level}]</span> {message}'
        self.console_log.append(formatted)
        self.console_log.moveCursor(QTextCursor.End)
        if level == "ERROR":
            self._set_status("Render failed", "error")
            self._show_console(True)
        elif "completed successfully" in message.lower():
            self._set_status("Render complete", "success")
        elif level == "WARNING":
            self._set_status("Needs attention", "warning")
            self._show_console(True)

    def clear_log(self) -> None:
        self.console_log.clear()
        self.progress_bar.setValue(0)
        self.progress_meta.setText("0%  ·  0 / 0 frames")
        self._set_status("Ready to render", "ready")

    def _set_status(self, text: str, state: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _show_console(self, visible: bool) -> None:
        self.console_log.setVisible(visible)
        self.console_toggle_btn.setText("Hide details" if visible else "Show details")

    def _toggle_console(self) -> None:
        self._show_console(not self.console_log.isVisible())
