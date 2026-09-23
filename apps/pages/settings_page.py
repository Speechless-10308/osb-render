import os
import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QFrame,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QScroller,
)

from src.config import Config
from apps.widgets import ToggleSwitch


def _get_user_config_dir() -> str:
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "osb-render")


def _get_user_config_path(config: Config | None = None) -> str:
    if config is not None and getattr(config.app, "config_dir", ""):
        if config.app.config_dir:
            return os.path.join(config.app.config_dir, "config.yaml")
    return os.path.join(_get_user_config_dir(), "config.yaml")


class SettingsPage(QWidget):
    """FFmpeg encoder, audio, and configuration settings. Auto-saves on change."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: Config | None = None
        self._populating = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        inner = QWidget()
        inner.setObjectName("settingsInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(26, 24, 26, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        title_col.addWidget(title)
        subtitle = QLabel("Configure video encoding, audio, and application preferences.")
        subtitle.setObjectName("pageSubtitle")
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        self.saved_status = QLabel("●  Saved automatically")
        self.saved_status.setObjectName("savedStatus")
        header.addWidget(self.saved_status, 0, Qt.AlignTop)
        layout.addLayout(header)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(14)

        enc_card = self._make_card("Video encoding")
        enc_grid = QGridLayout()
        enc_grid.setContentsMargins(0, 0, 0, 0)
        enc_grid.setHorizontalSpacing(16)
        enc_grid.setVerticalSpacing(8)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow",
        ])
        self.preset_combo.currentTextChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("Encoder preset", self.preset_combo), 0, 0)

        self.crf_spin = QSpinBox()
        self.crf_spin.setObjectName("crfSpin")
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setToolTip("0 is lossless, 23 is default, 51 is worst.")
        self.crf_spin.valueChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("CRF (quality)", self.crf_spin), 0, 1)

        self.sample_method_combo = QComboBox()
        self.sample_method_combo.addItems(["linear", "nearest"])
        self.sample_method_combo.setToolTip("Sampling method for image scaling.")
        self.sample_method_combo.currentTextChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("Sampling method", self.sample_method_combo), 1, 0)

        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.addItems(["yuv420p", "yuv444p", "yuv422p", "rgb24"])
        self.pixel_format_combo.setToolTip("Pixel format for output video.")
        self.pixel_format_combo.currentTextChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("Pixel format", self.pixel_format_combo), 1, 1)

        self.preset_tuning_combo = QComboBox()
        self.preset_tuning_combo.addItems([
            "default", "film", "animation", "grain", "stillimage", "psnr", "ssim",
        ])
        self.preset_tuning_combo.setToolTip("Tune encoder for specific content type.")
        self.preset_tuning_combo.currentTextChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("Preset tuning", self.preset_tuning_combo), 2, 0)

        self.gop_spin = QSpinBox()
        self.gop_spin.setRange(1, 600)
        self.gop_spin.setToolTip("GOP size (keyframe interval).")
        self.gop_spin.valueChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("GOP size", self.gop_spin), 2, 1)

        self.bframes_spin = QSpinBox()
        self.bframes_spin.setRange(0, 16)
        self.bframes_spin.setToolTip("Number of B-frames between I/P frames.")
        self.bframes_spin.valueChanged.connect(self._on_setting_changed)
        enc_grid.addLayout(self._field("B-frames", self.bframes_spin), 3, 0)
        enc_card.layout().addLayout(enc_grid)
        cards_row.addWidget(enc_card, 2)

        audio_card = self._make_card("Audio")
        audio_layout = audio_card.layout()
        self.audio_checkbox = ToggleSwitch("Enable audio merging")
        self.audio_checkbox.setObjectName("gpuToggle")
        self.audio_checkbox.toggled.connect(self._on_setting_changed)
        audio_layout.addWidget(self.audio_checkbox)
        audio_hint = QLabel("Merge the beatmap's audio track into the rendered video.")
        audio_hint.setObjectName("mutedLabel")
        audio_hint.setWordWrap(True)
        audio_layout.addWidget(audio_hint)
        audio_layout.addSpacing(6)

        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "mp3", "opus", "flac", "copy"])
        self.audio_codec_combo.currentTextChanged.connect(self._on_setting_changed)
        audio_layout.addLayout(self._field("Audio codec", self.audio_codec_combo))

        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["96k", "128k", "160k", "192k", "256k", "320k"])
        self.audio_bitrate_combo.currentTextChanged.connect(self._on_setting_changed)
        audio_layout.addLayout(self._field("Audio bitrate", self.audio_bitrate_combo))
        cards_row.addWidget(audio_card, 1)
        layout.addLayout(cards_row)

        cfg_card = self._make_card("Application")
        cfg_layout = cfg_card.layout()
        hint = QLabel("Settings are saved as soon as a value changes.")
        hint.setObjectName("mutedLabel")
        cfg_layout.addWidget(hint)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_label = QLabel("Configuration file")
        path_label.setObjectName("fieldLabel")
        path_row.addWidget(path_label)
        self.config_path_value = QLineEdit(_get_user_config_path())
        self.config_path_value.setObjectName("pathValue")
        self.config_path_value.setReadOnly(True)
        self.config_path_value.setToolTip("The directory used for the saved configuration.")
        path_row.addWidget(self.config_path_value, 1)
        self.change_path_btn = QPushButton("Change location")
        self.change_path_btn.setObjectName("browseBtn")
        self.change_path_btn.clicked.connect(self._change_config_path)
        path_row.addWidget(self.change_path_btn)
        cfg_layout.addLayout(path_row)

        reset_row = QHBoxLayout()
        reset_row.addStretch()
        self.reset_btn = QPushButton("Reset to defaults")
        self.reset_btn.setObjectName("secondaryBtn")
        self.reset_btn.clicked.connect(self._reset_defaults)
        reset_row.addWidget(self.reset_btn)
        cfg_layout.addLayout(reset_row)
        layout.addWidget(cfg_card)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    @staticmethod
    def _field(label_text: str, widget) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    @staticmethod
    def _make_card(title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(12)
        card_title = QLabel(title)
        card_title.setObjectName("cardTitle")
        card_layout.addWidget(card_title)
        return card

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_config(self, config: Config) -> None:
        self._config = config
        self._populating = True
        idx = self.preset_combo.findText(config.renderer.encoder_preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.crf_spin.setValue(config.renderer.crf)
        idx = self.sample_method_combo.findText(config.renderer.sample_method)
        if idx >= 0:
            self.sample_method_combo.setCurrentIndex(idx)
        idx = self.pixel_format_combo.findText(config.renderer.pixel_format)
        if idx >= 0:
            self.pixel_format_combo.setCurrentIndex(idx)
        idx = self.preset_tuning_combo.findText(config.renderer.preset_tuning)
        if idx >= 0:
            self.preset_tuning_combo.setCurrentIndex(idx)
        self.gop_spin.setValue(config.renderer.gop_size)
        self.bframes_spin.setValue(config.renderer.b_frames)
        self.audio_checkbox.setChecked(config.renderer.enable_audio)
        idx = self.audio_codec_combo.findText(config.renderer.audio_codec)
        if idx >= 0:
            self.audio_codec_combo.setCurrentIndex(idx)
        idx = self.audio_bitrate_combo.findText(config.renderer.audio_bitrate)
        if idx >= 0:
            self.audio_bitrate_combo.setCurrentIndex(idx)
        self.config_path_value.setText(_get_user_config_path(config))
        self._populating = False

    def set_theme(self, is_dark: bool) -> None:
        self.audio_checkbox.set_theme(is_dark)

    def save_config(self, config: Config) -> None:
        config.renderer.encoder_preset = self.preset_combo.currentText()
        config.renderer.crf = self.crf_spin.value()
        config.renderer.sample_method = self.sample_method_combo.currentText()
        config.renderer.pixel_format = self.pixel_format_combo.currentText()
        config.renderer.preset_tuning = self.preset_tuning_combo.currentText()
        config.renderer.gop_size = self.gop_spin.value()
        config.renderer.b_frames = self.bframes_spin.value()
        config.renderer.enable_audio = self.audio_checkbox.isChecked()
        config.renderer.audio_codec = self.audio_codec_combo.currentText()
        config.renderer.audio_bitrate = self.audio_bitrate_combo.currentText()

    def _on_setting_changed(self, *args) -> None:
        if self._populating or self._config is None:
            return
        self.save_config(self._config)
        try:
            self._config.to_yaml(_get_user_config_path(self._config))
        except OSError:
            self.saved_status.setText("●  Save failed")
            self.saved_status.setProperty("state", "error")
        else:
            self.saved_status.setText("●  Saved automatically")
            self.saved_status.setProperty("state", "success")
        self.saved_status.style().unpolish(self.saved_status)
        self.saved_status.style().polish(self.saved_status)

    def _change_config_path(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Config Directory", os.path.expanduser("~")
        )
        if dir_path and self._config:
            self._config.app.config_dir = dir_path
            new_path = os.path.join(dir_path, "config.yaml")
            self.config_path_value.setText(new_path)
            self._config.to_yaml(new_path)

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "This will reset all settings to their default values. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self._config:
            target_config = self._config
            default = Config()
            self.load_config(default)
            self.save_config(target_config)
            self._config = target_config
            self.config_path_value.setText(_get_user_config_path(target_config))
            self._on_setting_changed()
