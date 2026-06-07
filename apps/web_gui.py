"""pywebview-based GUI for OSBoard.

Replaces the PySide6 GUI with a WebView2-powered HTML/CSS/JS interface.
The rendering backend (RenderJob) is unchanged.
"""

import base64
import json
import os
import platform
import queue
import re
import sys
import threading
from typing import Any

import webview

from src.config import Config
from src.jobs import RenderJob, _resolve_ffmpeg


# ------------------------------------------------------------------
# Config helpers
# ------------------------------------------------------------------

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


def _get_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_ffmpeg_for_display(cfg: Config) -> str:
    """Return a human-readable ffmpeg path for the settings UI."""
    if cfg.renderer.ffmpeg_path and os.path.isfile(cfg.renderer.ffmpeg_path):
        return cfg.renderer.ffmpeg_path
    bundled = os.path.join(
        _get_project_root(),
        "ffmpeg.exe" if os.name == "nt" else "ffmpeg",
    )
    if os.path.isfile(bundled):
        return bundled + " (bundled)"
    return "ffmpeg (from PATH)"


# ------------------------------------------------------------------
# Render thread
# ------------------------------------------------------------------

class RenderThread(threading.Thread):
    """Background thread that runs RenderJob and posts events to a queue."""

    def __init__(self, config: Config, event_queue: queue.Queue):
        super().__init__(daemon=True)
        self.config = config
        self._event_queue = event_queue
        self._stop_event = threading.Event()
        self.job = RenderJob(self.config)

    def run(self):
        try:
            self.job.set_callbacks(
                progress_callback=self._on_progress,
                log_callback=self._on_log,
            )
            self.job.start()
            self._event_queue.put({"type": "finished", "success": True})
        except Exception:
            import traceback
            error_msg = f"Critical Error:\n{traceback.format_exc()}"
            self._event_queue.put({"type": "log", "message": error_msg, "level": "ERROR"})
            self._event_queue.put({"type": "finished", "success": False})

    def stop_task(self):
        self._event_queue.put({"type": "log", "message": "Stopping rendering...", "level": "WARNING"})
        self._stop_event.set()
        if self.job:
            self.job.stop()

    def _on_progress(self, current: int, total: int):
        self._event_queue.put({"type": "progress", "current": current, "total": total})

    def _on_log(self, message: str, level: str):
        self._event_queue.put({"type": "log", "message": message, "level": level})


# ------------------------------------------------------------------
# JS API exposed to the web frontend
# ------------------------------------------------------------------

class GuiAPI:
    """Methods callable from JavaScript via ``pywebview.api.<method>()``."""

    def __init__(self, gui: "WebGUI"):
        self._gui = gui

    def _make_file_types(self, pattern: str) -> list[str]:
        """Convert pattern to pywebview file_types format.
        Input: "OSU Files (*.osu)" -> ["OSU Files (*.osu)"]
        Input: "*.osu" -> ["OSU Files (*.osu)"]
        """
        if not pattern or not pattern.strip():
            return []
        parts = pattern.split("|") if "|" in pattern else [pattern]
        result = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if "(*." in p:
                result.append(p)  # already correct format
            else:
                # "*.osu" -> "OSU Files (*.osu)"
                ext = p.lstrip("*")
                result.append(f"{ext.upper()} Files ({p})")
        return result

    def select_file(self, title: str = "Select file", pattern: str = "*.*") -> str | None:
        """Open a native file dialog and return the selected path."""
        win = self._gui._window
        if win is None:
            return None
        result = win.create_file_dialog(
            dialog_type=webview.FileDialog.OPEN,
            directory=self._gui.config.path.osu_path or "",
            file_types=self._make_file_types(pattern),
        )
        return result[0] if result else None

    def save_file(self, title: str = "Save file", pattern: str = "*.mp4") -> str | None:
        """Open a native save dialog and return the chosen path."""
        win = self._gui._window
        if win is None:
            return None
        result = win.create_file_dialog(
            dialog_type=webview.FileDialog.SAVE,
            directory=os.path.dirname(self._gui.config.path.output_path or "") or "",
            file_types=self._make_file_types(pattern),
        )
        return result[0] if result else None

    def select_directory(self, title: str = "Select directory") -> str | None:
        """Open a native folder dialog and return the selected path."""
        win = self._gui._window
        if win is None:
            return None
        result = win.create_file_dialog(
            dialog_type=webview.FileDialog.FOLDER,
            directory=os.path.expanduser("~"),
        )
        return result[0] if result else None

    def select_ffmpeg_exe(self) -> str | None:
        """Open a file dialog specifically for ffmpeg.exe."""
        win = self._gui._window
        if win is None:
            return None
        result = win.create_file_dialog(
            dialog_type=webview.FileDialog.OPEN,
            directory="",
            file_types=["Executable (*.exe)"],
        )
        return result[0] if result else None

    def load_config(self) -> dict:
        """Return the full configuration as a JSON-serialisable dict."""
        return self._gui.config.model_dump()

    def save_config(self, config_dict: dict) -> None:
        """Save configuration from the frontend (Settings page)."""
        try:
            cfg = Config(**config_dict)
            self._gui.config = cfg
            cfg.to_yaml(_get_user_config_path(cfg))
        except Exception:
            r = self._gui.config.renderer
            rd = config_dict.get("renderer", {})
            if rd:
                for key in [
                    "encoder_preset", "crf", "sample_method", "pixel_format",
                    "preset_tuning", "gop_size", "b_frames", "use_gpu",
                    "enable_audio", "audio_codec", "audio_bitrate", "ffmpeg_path",
                ]:
                    if key in rd:
                        setattr(r, key, rd[key])
            a = self._gui.config.app
            ad = config_dict.get("app", {})
            if ad:
                for key in ["theme", "config_dir"]:
                    if key in ad:
                        setattr(a, key, ad[key])
            self._gui.config.to_yaml(_get_user_config_path(self._gui.config))

    def start_rendering(self, params: dict) -> None:
        """Start a render job with the given parameters."""
        self._gui._start_render(params)

    def stop_rendering(self) -> None:
        """Request the current render job to stop."""
        self._gui._stop_render()

    def poll_events(self) -> list[dict]:
        """Drain the event queue and return pending events."""
        return self._gui._drain_events()

    def get_default_ffmpeg(self) -> str:
        """Return the resolved ffmpeg path for display in settings."""
        return _resolve_ffmpeg_for_display(self._gui.config)

    def minimize_window(self) -> None:
        if self._gui._window:
            self._gui._window.minimize()

    def toggle_maximize(self) -> None:
        if self._gui._window:
            if self._gui._maximized:
                self._gui._window.restore()
            else:
                self._gui._window.maximize()
            self._gui._maximized = not self._gui._maximized

    def close_window(self) -> None:
        if self._gui._window:
            self._gui._window.destroy()

    def save_log_file(self, path: str, content: str) -> None:
        """Write log content to a file (called from JS export)."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_initial_state(self) -> dict:
        """Return the initial state for the frontend on load."""
        cfg = self._gui.config
        return {
            "osu_path": cfg.path.osu_path,
            "output_path": cfg.path.output_path,
            "width": cfg.renderer.width,
            "height": cfg.renderer.height,
            "fps": cfg.renderer.fps,
            "use_gpu": cfg.renderer.use_gpu,
            "encoder_preset": cfg.renderer.encoder_preset,
            "crf": cfg.renderer.crf,
            "theme": getattr(cfg.app, "theme", "dark"),
            "ffmpeg_path": cfg.renderer.ffmpeg_path,
            "ffmpeg_display": _resolve_ffmpeg_for_display(cfg),
        }


# ------------------------------------------------------------------
# WebGUI – window creation and lifecycle
# ------------------------------------------------------------------

class WebGUI:
    """Creates the pywebview window and manages the render lifecycle."""

    def __init__(self):
        self.config = _load_config()
        self._window: webview.Window | None = None
        self._render_thread: RenderThread | None = None
        self._event_queue: queue.Queue = queue.Queue()
        self._maximized = False

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def start(self) -> None:
        html = self._load_html()
        api = GuiAPI(self)

        self._window = webview.create_window(
            title="OSBoard",
            html=html,
            js_api=api,
            frameless=False,  # Use native window chrome for taskbar support
            width=1050,
            height=750,
            min_size=(900, 550),
        )

        webview.start(debug=False)

    def _load_html(self) -> str:
        """Read index.html and inline CSS/JS + image assets."""
        root = _get_project_root()
        html_path = os.path.join(root, "gui", "index.html")
        if not os.path.exists(html_path):
            alt = os.path.join(os.path.dirname(root), "gui", "index.html")
            if os.path.exists(alt):
                html_path = alt
            else:
                raise FileNotFoundError(
                    f"Could not find gui/index.html. Searched: {html_path}, {alt}"
                )

        gui_dir = os.path.dirname(html_path)

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Inline CSS
        def _inline_css(match):
            href = match.group(1)
            css_path = os.path.join(gui_dir, href)
            if os.path.exists(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    return f"<style>{f.read()}</style>"
            return match.group(0)

        html = re.sub(
            r'<link\s+rel="stylesheet"\s+href="([^"]+)"\s*/?>',
            _inline_css,
            html,
        )

        # Inline JS
        def _inline_js(match):
            src = match.group(1)
            js_path = os.path.join(gui_dir, src)
            if os.path.exists(js_path):
                with open(js_path, "r", encoding="utf-8") as f:
                    return f"<script>{f.read()}</script>"
            return match.group(0)

        html = re.sub(
            r'<script\s+src="([^"]+)"\s*>\s*</script>',
            _inline_js,
            html,
        )

        # Inline all img src references
        def _inline_img(match):
            img_src = match.group(1)
            # Resolve relative to gui dir
            img_path = os.path.normpath(os.path.join(gui_dir, img_src))
            if os.path.exists(img_path):
                ext = os.path.splitext(img_path)[1].lower()
                mime = {
                    ".svg": "image/svg+xml",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                }.get(ext, "image/png")
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                return match.group(0).replace(img_src, f"data:{mime};base64,{b64}")
            return match.group(0)

        html = re.sub(
            r'<img\s[^>]*src="([^"]+)"',
            _inline_img,
            html,
        )

        return html

    # ------------------------------------------------------------------
    # Render lifecycle
    # ------------------------------------------------------------------

    def _start_render(self, params: dict) -> None:
        """Called from JS API when user clicks Start."""
        if self._render_thread is not None and self._render_thread.is_alive():
            return

        self.config.path.osu_path = params.get("osu_path", "")
        self.config.path.output_path = params.get("output_path", "")
        self.config.renderer.width = int(params.get("width", 1920))
        self.config.renderer.height = int(params.get("height", 1080))
        self.config.renderer.fps = int(params.get("fps", 60))
        self.config.renderer.use_gpu = bool(params.get("use_gpu", True))
        self.config.renderer.encoder_preset = params.get("encoder_preset", "fast")
        self.config.renderer.crf = int(params.get("crf", 20))
        ffmpeg_path = params.get("ffmpeg_path", "")
        if ffmpeg_path:
            self.config.renderer.ffmpeg_path = ffmpeg_path
        if "enable_audio" in params:
            self.config.renderer.enable_audio = bool(params["enable_audio"])

        self.config.to_yaml(_get_user_config_path(self.config))

        self._render_thread = RenderThread(self.config, self._event_queue)
        self._render_thread.start()

    def _stop_render(self) -> None:
        if self._render_thread is not None and self._render_thread.is_alive():
            self._render_thread.stop_task()

    def _drain_events(self) -> list[dict]:
        events = []
        while True:
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events
