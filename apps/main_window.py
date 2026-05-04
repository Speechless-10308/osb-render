import os
import platform

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QApplication,
    QSizeGrip,
)
from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QPoint
from PySide6.QtGui import QColor

from apps.threads import RenderThread
from apps.sidebar import Sidebar
from apps.title_bar import TitleBar
from apps.custom_grips import CustomGrip
from apps.pages import HomePage, SettingsPage, AboutPage
from src.config import Config

WINDOW_MARGIN = 6


def _get_user_config_dir() -> str:
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "osb-render")


def _get_user_config_path(cfg: Config | None = None) -> str:
    default = os.path.join(_get_user_config_dir(), "config.yaml")
    if cfg is not None and getattr(cfg.app, "config_dir", "") and cfg.app.config_dir:
        return os.path.join(cfg.app.config_dir, "config.yaml")
    return default


def _load_config() -> Config:
    user_path = os.path.join(_get_user_config_dir(), "config.yaml")
    if os.path.exists(user_path):
        try:
            return Config.from_yaml(user_path)
        except Exception:
            pass

    repo_path = "configs/config.yaml"
    if os.path.exists(repo_path):
        try:
            return Config.from_yaml(repo_path)
        except Exception:
            pass

    return Config()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OSBoard")
        self.resize(1050, 750)
        self.setMinimumSize(900, 550)

        # Frameless
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.worker: RenderThread | None = None
        self.config = _load_config()
        self._maximized = False
        self._drag_pos: QPoint | None = None
        self._sidebar_anim: QPropertyAnimation | None = None

        self._setup_ui()
        self._connect_signals()
        self._load_state_from_config()
        self._setup_grips()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        # Outer widget wraps the entire window with margin for shadow
        outer = QWidget()
        outer.setObjectName("outerWidget")
        self.setCentralWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN)
        outer_layout.setSpacing(0)

        # Background frame with rounded corners and drop shadow
        self._bg_app = QFrame()
        self._bg_app.setObjectName("bgApp")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self._bg_app.setGraphicsEffect(shadow)

        outer_layout.addWidget(self._bg_app, stretch=1)

        # Inner layout inside bgApp
        inner = QVBoxLayout(self._bg_app)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # --- Title Bar ---
        self.title_bar = TitleBar()
        inner.addWidget(self.title_bar)

        # --- Content Area ---
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(Sidebar.SIDEBAR_COLLAPSED)
        self.sidebar.setFixedWidth(Sidebar.SIDEBAR_EXPANDED)
        content.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.settings_page = SettingsPage()
        self.about_page = AboutPage()

        self.stack.addWidget(self.home_page)     # 0
        self.stack.addWidget(self.settings_page) # 1
        self.stack.addWidget(self.about_page)    # 2

        content.addWidget(self.stack, stretch=1)

        inner.addLayout(content, stretch=1)

    def _setup_grips(self) -> None:
        self._left_grip = CustomGrip(self, Qt.LeftEdge)
        self._right_grip = CustomGrip(self, Qt.RightEdge)
        self._top_grip = CustomGrip(self, Qt.TopEdge)
        self._bottom_grip = CustomGrip(self, Qt.BottomEdge)

    # ------------------------------------------------------------------
    # Signal Wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        # Title bar
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_restore_requested.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self.title_bar.theme_toggle_btn.clicked.connect(self._toggle_theme)

        # Sidebar
        self.sidebar.toggled.connect(self._animate_sidebar)

        # Sidebar navigation
        self.sidebar.page_changed.connect(self.stack.setCurrentIndex)
        self.stack.currentChanged.connect(self._on_page_changed)

        # Home page actions
        self.home_page.browse_osu_requested.connect(self._browse_osu_file)
        self.home_page.browse_output_requested.connect(self._browse_output_file)
        self.home_page.start_requested.connect(self._start_rendering)
        self.home_page.stop_requested.connect(self._stop_rendering)

    def _load_state_from_config(self) -> None:
        self.home_page.set_file_paths(
            self.config.path.osu_path,
            self.config.path.output_path,
        )
        self.home_page.set_render_params(
            self.config.renderer.width,
            self.config.renderer.height,
            self.config.renderer.fps,
            self.config.renderer.use_gpu,
            encoder_preset=self.config.renderer.encoder_preset,
            crf=self.config.renderer.crf,
        )
        self.settings_page.load_config(self.config)

        # Theme
        theme = getattr(self.config.app, "theme", "dark")
        self._apply_theme(theme)

    def _on_page_changed(self, index: int) -> None:
        if index == 1:
            self.settings_page.load_config(self.config)

    # ------------------------------------------------------------------
    # Sidebar Animation
    # ------------------------------------------------------------------

    def _toggle_sidebar(self) -> None:
        self.sidebar.toggle()

    def _animate_sidebar(self, expanded: bool) -> None:
        if self._sidebar_anim is not None and self._sidebar_anim.state() == QPropertyAnimation.Running:
            self._sidebar_anim.stop()

        start = self.sidebar.width()
        end = Sidebar.SIDEBAR_EXPANDED if expanded else Sidebar.SIDEBAR_COLLAPSED

        self._sidebar_anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self._sidebar_anim.setDuration(400)
        self._sidebar_anim.setStartValue(start)
        self._sidebar_anim.setEndValue(end)
        self._sidebar_anim.setEasingCurve(QEasingCurve.InOutQuart)
        self._sidebar_anim.start()

        self._sidebar_width_anim = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self._sidebar_width_anim.setDuration(400)
        self._sidebar_width_anim.setStartValue(start)
        self._sidebar_width_anim.setEndValue(end)
        self._sidebar_width_anim.setEasingCurve(QEasingCurve.InOutQuart)
        self._sidebar_width_anim.start()

    # ------------------------------------------------------------------
    # Theme Toggle
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        current = getattr(self.config.app, "theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self._apply_theme(new_theme)
        self.config.app.theme = new_theme
        self.config.to_yaml(_get_user_config_path(self.config))

    def _apply_theme(self, theme: str) -> None:
        import sys
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qss_path = os.path.join(base, "themes", f"osboard_{theme}.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())

        is_dark = theme == "dark"
        self.title_bar.set_theme(is_dark)
        self.sidebar.set_theme_icons(is_dark)
        self.home_page.set_theme_icons(is_dark)

    # ------------------------------------------------------------------
    # Maximize / Restore
    # ------------------------------------------------------------------

    def _toggle_maximize(self) -> None:
        if self._maximized:
            self.showNormal()
            self._maximized = False
            # Restore margins for shadow
            self.centralWidget().layout().setContentsMargins(
                WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN
            )
        else:
            self.showMaximized()
            self._maximized = True
            self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)

        self.title_bar.set_maximized_state(self._maximized)

    # ------------------------------------------------------------------
    # Window Drag (from title bar inside bgApp)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            if self._maximized:
                self._toggle_maximize()
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ------------------------------------------------------------------
    # Resize — Update grips
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_left_grip"):
            self._left_grip.setGeometry(0, 10, 10, self.height())
            self._right_grip.setGeometry(self.width() - 10, 10, 10, self.height())
            self._top_grip.setGeometry(0, 0, self.width(), 10)
            self._bottom_grip.setGeometry(0, self.height() - 10, self.width(), 10)

    # ------------------------------------------------------------------
    # File Browsing
    # ------------------------------------------------------------------

    def _browse_osu_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select .osu file", "", "OSU Files (*.osu)"
        )
        if path:
            self.home_page.set_osu_path(path)
            base = os.path.splitext(path)[0]
            self.home_page.set_output_path(base + ".mp4")

    def _browse_output_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output Video", "", "MP4 Files (*.mp4);;All Files (*)"
        )
        if path:
            self.home_page.set_output_path(path)

    # ------------------------------------------------------------------
    # Render Lifecycle
    # ------------------------------------------------------------------

    def _start_rendering(self) -> None:
        osu_path, output_path = self.home_page.get_file_paths()

        if not osu_path or not os.path.isfile(osu_path):
            QMessageBox.critical(self, "Error", "Please select a valid .osu file.")
            return

        self.home_page.set_rendering_state(True)
        self.home_page.clear_log()
        self.home_page.update_progress(0, 1)

        # Collect params from UI
        params = self.home_page.get_render_params()
        self.config.path.osu_path = osu_path
        self.config.path.output_path = output_path
        self.config.renderer.width = params["width"]
        self.config.renderer.height = params["height"]
        self.config.renderer.fps = params["fps"]
        self.config.renderer.use_gpu = params["use_gpu"]
        self.config.renderer.encoder_preset = params["encoder_preset"]
        self.config.renderer.crf = params["crf"]

        # Pull settings page values
        self.settings_page.save_config(self.config)

        # Persist
        self.config.to_yaml(_get_user_config_path(self.config))

        self.home_page.append_log("Starting rendering...", "INFO")

        self.worker = RenderThread(config=self.config)
        self.worker.progress_signal.connect(self.home_page.update_progress)
        self.worker.log_signal.connect(self.home_page.append_log)
        self.worker.finished_signal.connect(self._rendering_finished)
        self.worker.start()

    def _stop_rendering(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop_task()
            self.home_page.append_log(
                "Stop requested. Waiting for current frame to finish...", "WARNING"
            )
            self.home_page.stop_btn.setEnabled(False)

    def _rendering_finished(self, success: bool) -> None:
        if success:
            self.home_page.append_log("Rendering completed successfully.", "INFO")
        else:
            self.home_page.append_log("Rendering failed.", "ERROR")
        self.home_page.set_rendering_state(False)
