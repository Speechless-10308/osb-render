import os
from apps.threads import RenderThread
from apps.dialogs import AdvancedSettingsDialog
from apps.widgets import ResolutionWidget

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QPushButton,
    QFrame,
)
from PySide6.QtGui import QIcon, QTextCursor

from src.config import Config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Osu! Storyboard Renderer")
        self.resize(500, 300)

        self.worker = None
        self.default_config_path = "configs/config.yaml"
        self.config = Config()
        if os.path.exists(self.default_config_path):
            try:
                self.config = Config.from_yaml(self.default_config_path)
            except:
                self.log_message("Failed to load default config.", "ERROR")
                pass

        self.aspect_ratio = self.config.renderer.width / self.config.renderer.height
        self.setup_ui()

        self.res_widget.set_values(
            self.config.renderer.width, self.config.renderer.height
        )
        self.fps_spin.setValue(self.config.renderer.fps)
        self.gpu_checkbox.setChecked(self.config.renderer.use_gpu)
        self.osu_path_edit.setText(self.config.path.osu_path)
        self.out_path_edit.setText(self.config.path.output_path)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File choser layout
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()

        self.osu_path_edit = QLineEdit()
        self.browse_osu_button = QPushButton("Browse")
        self.browse_osu_button.clicked.connect(self.browse_osu_file)

        osu_row = QHBoxLayout()
        osu_row.addWidget(self.osu_path_edit)
        osu_row.addWidget(self.browse_osu_button)
        file_layout.addRow(QLabel(".osu File:"), osu_row)

        self.out_path_edit = QLineEdit()
        self.browse_out_button = QPushButton("Save As")
        self.browse_out_button.clicked.connect(self.browse_output_file)

        out_row = QHBoxLayout()
        out_row.addWidget(self.out_path_edit)
        out_row.addWidget(self.browse_out_button)
        file_layout.addRow(QLabel("Output Video:"), out_row)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        settings_group = QGroupBox("Rendering Settings")
        settings_layout = QHBoxLayout()

        self.res_widget = ResolutionWidget(
            self.config.renderer.width, self.config.renderer.height
        )
        settings_layout.addWidget(self.res_widget)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        settings_layout.addWidget(line)

        params_layout = QVBoxLayout()

        simple_settings_layout = QHBoxLayout()

        # fps setting
        fps_layout = QHBoxLayout()
        fps_label = QLabel("FPS:")
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 999)
        self.fps_spin.setValue(60)
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        simple_settings_layout.addLayout(fps_layout)

        # gpu checkbox
        self.gpu_checkbox = QCheckBox("Use GPU Acceleration")
        self.gpu_checkbox.setChecked(True)
        simple_settings_layout.addWidget(self.gpu_checkbox)

        params_layout.addLayout(simple_settings_layout)

        self.adv_settings_btn = QPushButton("Advanced Settings...")
        self.adv_settings_btn.clicked.connect(self.open_advanced_settings)
        params_layout.addWidget(self.adv_settings_btn)

        params_layout.addStretch()

        settings_layout.addLayout(params_layout)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Render button
        render_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Rendering")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #2E3B2F;
                color: #888;
            }
            """
        )
        self.start_btn.clicked.connect(self.start_rendering)

        self.stop_btn = QPushButton("Stop Rendering")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336; 
                color: white; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #3e1f1f;
                color: #888;
            }
            """
        )
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_rendering)

        render_layout.addWidget(self.start_btn)
        render_layout.addWidget(self.stop_btn)
        main_layout.addLayout(render_layout)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setFormat("%p% (%v/%m frames)")
        main_layout.addWidget(self.pbar)

        # log view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color: #2b2b2b; color: #dcdcdc; font-family: Consolas;"
        )
        main_layout.addWidget(self.log_view)

    def browse_osu_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select .osu file", "", "OSU Files (*.osu)"
        )
        if path:
            self.osu_path_edit.setText(path)
            base = os.path.splitext(path)[0]
            self.out_path_edit.setText(base + ".mp4")

    def browse_output_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output Video", "", "MP4 Files (*.mp4);;All Files (*)"
        )
        if path:
            self.out_path_edit.setText(path)

    def open_advanced_settings(self):
        dialog = AdvancedSettingsDialog(cfg=self.config, parent=self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.config.renderer.encoder_preset = settings["encoder_preset"]
            self.config.renderer.crf = settings["crf"]
            self.config.renderer.sample_method = settings["sample_method"]
            self.config.renderer.enable_audio = settings["enable_audio"]

    def log_message(self, message: str, level: str):
        color = "#dcdcdc"
        if level == "ERROR":
            color = "#ff5555"
        elif level == "WARNING":
            color = "#ffb86c"
        elif level == "INFO":
            color = "#50fa7b"

        formatted_msg = f'<span style="color:{color}">[{level}]</span> {message}'
        self.log_view.append(formatted_msg)
        self.log_view.moveCursor(QTextCursor.End)

    def update_progress(self, current: int, total: int):
        self.pbar.setMaximum(total)
        self.pbar.setValue(current)

    def start_rendering(self):
        osu_path = self.osu_path_edit.text()

        if not osu_path or not os.path.isfile(osu_path):
            QMessageBox.critical(self, "Error", "Please select a valid .osu file.")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.osu_path_edit.setEnabled(False)
        self.out_path_edit.setEnabled(False)
        self.browse_osu_button.setEnabled(False)
        self.browse_out_button.setEnabled(False)
        self.log_view.clear()
        self.pbar.setValue(0)

        self.log_message("Starting rendering...", "INFO")

        cfg = self.config if hasattr(self, "config") else Config()
        cfg.path.osu_path = osu_path
        cfg.path.output_path = self.out_path_edit.text()
        width, height = self.res_widget.get_values()
        cfg.renderer.width = width
        cfg.renderer.height = height
        cfg.renderer.fps = self.fps_spin.value()
        cfg.renderer.use_gpu = self.gpu_checkbox.isChecked()

        cfg.to_yaml("configs/config.yaml")

        self.worker = RenderThread(config=cfg)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.rendering_finished)
        self.worker.start()

    def rendering_finished(self, success: bool):
        if success:
            self.log_message("Rendering completed successfully.", "INFO")
        else:
            self.log_message("Rendering failed.", "ERROR")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.osu_path_edit.setEnabled(True)
        self.out_path_edit.setEnabled(True)
        self.browse_osu_button.setEnabled(True)
        self.browse_out_button.setEnabled(True)

    def stop_rendering(self):
        if self.worker:
            self.worker.stop_task()
            self.log_message(
                "Stop requested. Waiting for current frame to finish...", "WARNING"
            )
            self.stop_btn.setEnabled(False)
