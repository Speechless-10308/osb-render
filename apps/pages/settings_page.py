import os
import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QFrame,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
    QScroller,
)

from src.config import Config


def _get_user_config_dir() -> str:
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "osb-render")


def _get_user_config_path() -> str:
    return os.path.join(_get_user_config_dir(), "config.yaml")


class SettingsPage(QWidget):
    """FFmpeg encoder, audio, and configuration settings. Auto-saves on change."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: Config | None = None
        self._populating = False

        # Outer layout for the page
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area wraps all content
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # Inner widget inside scroll area
        inner = QWidget()
        inner.setObjectName("settingsInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Page title
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # --- FFmpeg Encoding Card ---
        enc_card = self._make_card("FFmpeg Encoding")
        form = QFormLayout()
        form.setSpacing(10)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow",
        ])
        self.preset_combo.currentTextChanged.connect(self._on_setting_changed)
        form.addRow("Encoder Preset:", self.preset_combo)

        self.crf_spin = QSpinBox()
        self.crf_spin.setObjectName("crfSpin")
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setToolTip("0 is lossless, 23 is default, 51 is worst.")
        self.crf_spin.valueChanged.connect(self._on_setting_changed)
        form.addRow("CRF (Quality):", self.crf_spin)

        self.sample_method_combo = QComboBox()
        self.sample_method_combo.addItems(["linear", "nearest"])
        self.sample_method_combo.setToolTip("Sampling method for image scaling.")
        self.sample_method_combo.currentTextChanged.connect(self._on_setting_changed)
        form.addRow("Sampling Method:", self.sample_method_combo)

        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.addItems(["yuv420p", "yuv444p", "yuv422p", "rgb24"])
        self.pixel_format_combo.setToolTip("Pixel format for output video.")
        self.pixel_format_combo.currentTextChanged.connect(self._on_setting_changed)
        form.addRow("Pixel Format:", self.pixel_format_combo)

        self.preset_tuning_combo = QComboBox()
        self.preset_tuning_combo.addItems([
            "default", "film", "animation", "grain", "stillimage", "psnr", "ssim",
        ])
        self.preset_tuning_combo.setToolTip("Tune encoder for specific content type.")
        self.preset_tuning_combo.currentTextChanged.connect(self._on_setting_changed)
        form.addRow("Preset Tuning:", self.preset_tuning_combo)

        self.gop_spin = QSpinBox()
        self.gop_spin.setRange(1, 600)
        self.gop_spin.setToolTip("GOP size (keyframe interval).")
        self.gop_spin.valueChanged.connect(self._on_setting_changed)
        form.addRow("GOP Size:", self.gop_spin)

        self.bframes_spin = QSpinBox()
        self.bframes_spin.setRange(0, 16)
        self.bframes_spin.setToolTip("Number of B-frames between I/P frames.")
        self.bframes_spin.valueChanged.connect(self._on_setting_changed)
        form.addRow("B-Frames:", self.bframes_spin)

        enc_card.layout().addLayout(form)
        layout.addWidget(enc_card)

        # --- Audio Card ---
        audio_card = self._make_card("Audio")
        audio_layout = audio_card.layout()

        self.audio_checkbox = QCheckBox("Enable Audio Merging")
        self.audio_checkbox.toggled.connect(self._on_setting_changed)
        audio_layout.addWidget(self.audio_checkbox)

        audio_hint = QLabel("Merges the beatmap's audio track into the rendered video.")
        audio_hint.setObjectName("mutedLabel")
        audio_hint.setWordWrap(True)
        audio_layout.addWidget(audio_hint)

        audio_form = QFormLayout()
        audio_form.setSpacing(10)

        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "mp3", "opus", "flac", "copy"])
        self.audio_codec_combo.currentTextChanged.connect(self._on_setting_changed)
        audio_form.addRow("Audio Codec:", self.audio_codec_combo)

        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems([
            "96k", "128k", "160k", "192k", "256k", "320k",
        ])
        self.audio_bitrate_combo.setCurrentIndex(3)
        self.audio_bitrate_combo.currentTextChanged.connect(self._on_setting_changed)
        audio_form.addRow("Audio Bitrate:", self.audio_bitrate_combo)

        audio_layout.addLayout(audio_form)
        layout.addWidget(audio_card)

        # --- Configuration Card ---
        cfg_card = self._make_card("Configuration")

        hint = QLabel("Settings are automatically saved when any value changes.")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        cfg_card.layout().addWidget(hint)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        path_label = QLabel("Config location:")
        path_label.setObjectName("mutedLabel")
        path_row.addWidget(path_label)

        self.config_path_value = QLabel(_get_user_config_path())
        self.config_path_value.setObjectName("pathLabel")
        flags = self.config_path_value.textInteractionFlags()
        self.config_path_value.setTextInteractionFlags(
            flags | Qt.TextSelectableByMouse
        )
        self.config_path_value.setWordWrap(True)
        path_row.addWidget(self.config_path_value, stretch=1)

        self.change_path_btn = QPushButton("Change...")
        self.change_path_btn.setObjectName("browseBtn")
        self.change_path_btn.clicked.connect(self._change_config_path)
        path_row.addWidget(self.change_path_btn)

        cfg_card.layout().addLayout(path_row)

        # Reset button
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setObjectName("secondaryBtn")
        self.reset_btn.clicked.connect(self._reset_defaults)
        reset_row.addWidget(self.reset_btn)
        cfg_card.layout().addLayout(reset_row)

        layout.addWidget(cfg_card)

        # Bottom spacer
        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _make_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
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

        config_path = _get_user_config_path()
        if getattr(config.app, "config_dir", "") and config.app.config_dir:
            config_path = os.path.join(config.app.config_dir, "config.yaml")
        self.config_path_value.setText(config_path)

        self._populating = False

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
            default = Config()
            self.load_config(default)
            self.save_config(self._config)
