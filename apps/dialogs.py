from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QCheckBox,
)

from src.config import Config


class AdvancedSettingsDialog(QDialog):
    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.resize(300, 150)
        self.cfg = cfg

        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.preset_combo = QComboBox()
        presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ]  # the ffmpeg presets
        self.preset_combo.addItems(presets)
        current_preset = self.cfg.renderer.encoder_preset
        index = self.preset_combo.findText(current_preset)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        layout.addRow("Encoder Preset:", self.preset_combo)

        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setToolTip("0 is lossless, 23 is default, 51 is worst.")
        self.crf_spin.setValue(self.cfg.renderer.crf)
        layout.addRow("CRF (Quality):", self.crf_spin)

        self.sample_method_combo = QComboBox()
        self.sample_method_combo.addItems(["linear", "nearest"])
        self.sample_method_combo.setToolTip(
            "Sampling method for image scaling, linear is smoother but much slower, while nearest is faster but blockier."
        )
        current_method = self.cfg.renderer.sample_method
        index = self.sample_method_combo.findText(current_method)
        if index >= 0:
            self.sample_method_combo.setCurrentIndex(index)
        layout.addRow("Sampling Method:", self.sample_method_combo)

        self.audio_checkbox = QCheckBox("Enable Audio")
        self.audio_checkbox.setChecked(self.cfg.renderer.enable_audio)
        layout.addRow(self.audio_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_settings(self):
        return {
            "encoder_preset": self.preset_combo.currentText(),
            "crf": self.crf_spin.value(),
            "sample_method": self.sample_method_combo.currentText(),
            "enable_audio": self.audio_checkbox.isChecked(),
        }
