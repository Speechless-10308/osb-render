import os
import re
import subprocess
import threading
from typing import Optional

import skia
from loguru import logger


class VideoSource:
    """
    Decodes video frames via a single ffmpeg pipe in a background thread.

    A single ffmpeg subprocess decodes all frames to raw RGBA on stdout.
    A background thread reads frames as fast as ffmpeg produces them and
    stores decoded ``skia.Image`` objects in a bounded buffer.  The main
    thread retrieves frames by index — O(1) on the hot path.

    Backpressure keeps memory bounded: the decode thread blocks when the
    buffer reaches *BUFFER_SIZE* frames.  Old frames (behind the current
    read position) are evicted by the consumer to free slots.
    """

    _BUFFER_SIZE = 90  # decoded frames kept ready (~1.5 s at 60 fps)

    def __init__(self, video_path: str, ffmpeg_path: str = "ffmpeg"):
        self.video_path = video_path
        self.ffmpeg = ffmpeg_path

        self.width: int = 0
        self.height: int = 0
        self.fps: float = 30.0
        self.duration_ms: int = 0
        self.total_frames: int = 0

        self._pipe: subprocess.Popen | None = None
        self._frame_bytes: int = 0
        self._next_idx: int = 0       # next frame the bg thread will write
        self._done: bool = False

        self._frames: dict[int, skia.Image] = {}
        self._cv = threading.Condition()

        if not os.path.isfile(video_path):
            logger.warning(f"Video file not found: {video_path}")
            return

        self._probe()
        if self.is_valid:
            self._start_pipe()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _probe(self):
        """Extract resolution, fps and duration from ffmpeg stderr output."""
        cmd = [self.ffmpeg, "-nostats", "-i", self.video_path, "-f", "null", "NUL"]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.error(f"Failed to probe video: {self.video_path}")
            return

        info = proc.stderr

        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", info)
        if dur_match:
            h, m, s, cs = map(int, dur_match.groups())
            self.duration_ms = ((h * 60 + m) * 60 + s) * 1000 + cs * 10

        stream_match = re.search(
            r"Video:.*?(\d{2,5})x(\d{2,5})[,\s].*?([\d.]+)\s*fps", info
        )
        if stream_match:
            self.width = int(stream_match.group(1))
            self.height = int(stream_match.group(2))
            self.fps = float(stream_match.group(3))

        if self.fps > 0 and self.duration_ms > 0:
            self.total_frames = int(self.duration_ms * self.fps / 1000) + 1

        logger.info(
            f"Video: {self.width}x{self.height} {self.fps}fps "
            f"{self.duration_ms}ms {self.total_frames}frames"
        )

    # ------------------------------------------------------------------
    # Background decode (producer)
    # ------------------------------------------------------------------

    def _start_pipe(self):
        """Launch ffmpeg pipe and a background thread that reads all frames."""
        cmd = [
            self.ffmpeg,
            "-loglevel", "error",
            "-nostats",
            "-i", self.video_path,
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "pipe:1",
        ]
        try:
            self._pipe = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.error("ffmpeg not found — video disabled")
            self._pipe = None
            return

        self._frame_bytes = self.width * self.height * 4

        t = threading.Thread(target=self._decode_loop, daemon=True)
        t.start()

    def _decode_loop(self):
        """Continuously read raw frames from the pipe; block when buffer full.

        If the consumer does not catch up within 0.1 s the oldest buffered
        frame is evicted — this handles the rare case where the first
        requested frame is far from the start (e.g. debug mode).
        """
        while True:
            try:
                chunk = self._pipe.stdout.read(self._frame_bytes)
            except ValueError:
                break  # pipe closed during shutdown
            if len(chunk) < self._frame_bytes:
                break

            img = self._bytes_to_image(chunk)
            with self._cv:
                while len(self._frames) >= self._BUFFER_SIZE:
                    if not self._cv.wait(timeout=0.1):
                        # Consumer is too far behind — drop the oldest frame
                        oldest = min(self._frames.keys())
                        del self._frames[oldest]
                self._frames[self._next_idx] = img
                self._next_idx += 1
                self._cv.notify_all()

        with self._cv:
            self._done = True
            self._cv.notify_all()

    # ------------------------------------------------------------------
    # Frame access  (consumer — hot path, called once per output frame)
    # ------------------------------------------------------------------

    def get_frame(self, time_ms: int) -> Optional[skia.Image]:
        """Return the video frame at *time_ms* within the video.

        Returns None before start or after end.  O(1) dict lookup once
        the decode thread has reached the requested index.
        """
        if self.total_frames <= 0:
            return None

        if time_ms < 0 or time_ms > self.duration_ms:
            return None

        frame_idx = int(time_ms * self.fps / 1000)
        if frame_idx >= self.total_frames:
            return None

        with self._cv:
            # Wait until the frame is decoded (or we know it never will be)
            while frame_idx not in self._frames:
                if self._done and frame_idx >= self._next_idx:
                    return None
                self._cv.wait()

            # Evict frames the consumer is done with so the producer
            # can keep decoding ahead.  Keep a 2-frame margin because
            # the same video frame often serves multiple output frames.
            cutoff = frame_idx - 2
            if cutoff >= 0:
                for k in list(self._frames):
                    if k < cutoff:
                        del self._frames[k]

            self._cv.notify_all()
            return self._frames[frame_idx]

    def _bytes_to_image(self, data: bytes) -> skia.Image:
        return skia.Image.frombytes(
            data,
            skia.ISize(self.width, self.height),
            skia.kRGBA_8888_ColorType,
            skia.kUnpremul_AlphaType,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        return self.total_frames > 0

    def close(self):
        if self._pipe is not None:
            try:
                self._pipe.stdout.close()
                self._pipe.terminate()
                self._pipe.wait(timeout=5)
            except Exception:
                self._pipe.kill()
            self._pipe = None
