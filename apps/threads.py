from PySide6.QtCore import Qt, QThread, Signal, Slot

from src.config import Config
from src.jobs import RenderJob


class RenderThread(QThread):
    """
    A background thread to run the rendering job.
    Turns signals to update the GUI.
    """

    progress_signal = Signal(int, int)
    log_signal = Signal(str, str)
    finished_signal = Signal(bool)

    def __init__(self, config: Config):
        super().__init__()
        self.config: Config = config
        self.job: RenderJob = None

    def run(self):
        try:
            self.job = RenderJob(self.config)
            self.job.set_callbacks(
                progress_callback=self._on_progress,
                log_callback=self._on_log,
            )

            self.job.start()

            self.finished_signal.emit(True)

        except Exception as e:
            import traceback

            error_msg = f"Critical Error:\n{traceback.format_exc()}"
            self.log_signal.emit(error_msg, "ERROR")
            self.finished_signal.emit(False)

    def stop_task(self):
        if self.job:
            self.log_signal.emit("Stopping rendering...", "WARNING")
            self.job.stop()

    def _on_progress(self, current: int, total: int):
        self.progress_signal.emit(current, total)

    def _on_log(self, message: str, level: str):
        self.log_signal.emit(message, level)
