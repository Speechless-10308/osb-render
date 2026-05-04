import multiprocessing
import os
import subprocess
import threading
from typing import Callable, List, Optional
from src.parser import StoryboardParser
from src.models import Storyboard
from src.config import Config
from src.render_skia import SkiaRenderer, SkiaRendererGpu
from src.state_engine import StateEngine
from src.managers import AssetLoader

from loguru import logger
import re
import skia
import numpy as np
from src.video import VideoSource
from src.models import VideoObject

# Multiprocessing needs these at module level to be picklable, but who use cpu models anyway?
worker_renderer: Optional[SkiaRenderer] = None


def init_worker(
    engine: StateEngine,
    asset_path: str,
    width: int,
    height: int,
    video_path: str | None = None,
    video_object: VideoObject | None = None,
):
    global worker_renderer
    assets_loader = AssetLoader(base_path=asset_path)
    video_source = None
    if video_path and os.path.isfile(video_path):
        ffmpeg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ffmpeg.exe" if os.name == "nt" else "ffmpeg",
        )
        video_source = VideoSource(video_path, ffmpeg_path=ffmpeg)
    worker_renderer = SkiaRenderer(
        engine,
        assets_loader,
        width=width,
        height=height,
        video_source=video_source,
        video_object=video_object,
    )


def render_frame_worker(time_ms: int) -> bytes:
    global worker_renderer
    if worker_renderer is None:
        logger.error("Worker renderer not initialized")
        raise RuntimeError("Worker renderer not initialized")
    return worker_renderer.render_frame(time_ms).tobytes()


def get_audio_from_osu(osu_path: str) -> str:
    with open(osu_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("AudioFilename"):
                audio_name = line.split(":", 1)[1].strip()
                return audio_name
    return ""


def log_message(message: str, level: str = "INFO"):
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    else:
        logger.debug(message)


class RenderJob:
    def __init__(self, config: Config):
        self.cfg: Config = config

        self._stop_event = threading.Event()
        self.base_path: str = os.path.dirname(self.cfg.path.osu_path)

        osu_path = self.cfg.path.osu_path
        self.audio_path: str = os.path.join(
            self.base_path, get_audio_from_osu(osu_path)
        )
        # like "xx - x [xx].osu" => "xx - x.osb"
        filename = os.path.splitext(os.path.basename(osu_path))[0]
        filename = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]\s*$", "", filename)
        self.osb_path: str = os.path.join(self.base_path, filename + ".osb")

        self.progress_callback: Callable[[int, int], None] | None = None
        self.log_callback: Callable[[str, str], None] = log_message

    def set_callbacks(
        self,
        progress_callback: Callable[[int, int], None],
        log_callback: Callable[[str, str], None] = log_message,
    ):
        self.progress_callback = progress_callback
        self.log_callback = log_callback

    def stop(self):
        self._stop_event.set()

    def _get_video_duration(self, storyboard: Storyboard) -> int:
        max_time = 0
        layers = [
            storyboard.background_layer,
            storyboard.fail_layer,
            storyboard.pass_layer,
            storyboard.foreground_layer,
            storyboard.overlay_layer,
        ]

        for layer in layers:
            for obj in layer:
                obj_end_time = obj.life_end
                if obj_end_time > max_time:
                    max_time = obj_end_time

        # Video playback extends the total duration
        if storyboard.video is not None and self._video_source is not None:
            video_end = storyboard.video.start_time + self._video_source.duration_ms
            if video_end > max_time:
                max_time = video_end

        return max_time

    def _build_ffmpeg_command(self) -> List[str]:
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{self.cfg.renderer.width}x{self.cfg.renderer.height}",
            "-pix_fmt",
            "rgba",
            "-r",
            str(self.cfg.renderer.fps),
            "-i",
            "-",  # Input from stdin
            "-c:v",
            "libx264",  # Video codec
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",  # Output pixel format
            "-crf",
            str(self.cfg.renderer.crf),  # Quality
            self.cfg.path.output_path,
        ]
        return ffmpeg_cmd

    def start(self):
        # Parse storyboard events from the .osu file first.
        # osu! renders .osu storyboard objects before .osb objects within
        # each layer, so .osu forms the base and .osb is merged on top.
        self.log_callback(
            f"Parsing storyboard from .osu: {self.cfg.path.osu_path}", "INFO"
        )
        sb_parser = StoryboardParser()
        try:
            storyboard = sb_parser.parse(self.cfg.path.osu_path)
        except Exception as e:
            self.log_callback(f"Error parsing .osu storyboard: {e}", "ERROR")
            return

        if os.path.exists(self.osb_path):
            self.log_callback(
                f"Parsing storyboard from .osb: {self.osb_path}", "INFO"
            )
            osb_parser = StoryboardParser()
            try:
                osb_storyboard = osb_parser.parse(self.osb_path)
                storyboard.merge(osb_storyboard)
            except Exception as e:
                self.log_callback(f"Error parsing .osb storyboard: {e}", "ERROR")
                return
        else:
            self.log_callback(
                f"OSB file not found at '{self.osb_path}', using .osu events only.",
                "WARNING",
            )

        if storyboard.is_empty():
            self.log_callback(
                "Error: No storyboard objects found in .osu or .osb file.", "ERROR"
            )
            return

        # Initialise video source if the .osu defines a video event
        self._video_source: VideoSource | None = None
        if storyboard.video is not None:
            video_path = os.path.join(
                self.base_path, storyboard.video.filepath
            )
            ffmpeg_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "ffmpeg.exe" if os.name == "nt" else "ffmpeg",
            )
            self._video_source = VideoSource(video_path, ffmpeg_path=ffmpeg_path)
            if not self._video_source.is_valid:
                self.log_callback(
                    f"Failed to load video: {video_path}", "WARNING"
                )

        engine = StateEngine(storyboard)
        total_duration = self._get_video_duration(storyboard)
        self.log_callback(f"Total video duration: {total_duration} ms", "INFO")

        total_frames = (total_duration * self.cfg.renderer.fps) // 1000 + 1

        ffmpeg_cmd = self._build_ffmpeg_command()
        self.log_callback(
            f"Starting ffmpeg with command: {' '.join(ffmpeg_cmd)}", "INFO"
        )

        process = subprocess.Popen(
            ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL
        )

        try:
            if self.cfg.renderer.use_gpu:
                self._render_gpu(process, engine, total_frames)
            else:
                self._render_cpu(process, engine, total_frames)
        except KeyboardInterrupt:
            self.log_callback("Rendering interrupted by user.", "WARNING")
            self.stop()
        except Exception as e:
            self.log_callback(f"Error during rendering: {e}", "ERROR")
        finally:
            if process.stdin:
                process.stdin.close()
            process.wait()

        if not self._stop_event.is_set():
            self.log_callback(
                f"Rendering completed successfully. Video saved to {self.cfg.path.output_path}",
                "INFO",
            )
            self._merge_audio()
        else:
            self.log_callback("Rendering was stopped before completion.", "WARNING")

    def _render_gpu(
        self, process: subprocess.Popen, engine: StateEngine, total_frames: int
    ):
        self.log_callback(
            f"Using GPU acceleration for rendering with {total_frames} frames.", "INFO"
        )

        vo = engine.storyboard.video
        renderer = SkiaRendererGpu(
            engine,
            AssetLoader(base_path=self.base_path),
            self.cfg.renderer.width,
            self.cfg.renderer.height,
            self.cfg.renderer.sample_method,
            video_source=self._video_source,
            video_object=vo,
        )
        for i in range(total_frames):
            if self._stop_event.is_set():
                break
            time_ms = int(i * 1000 / self.cfg.renderer.fps)
            frame = renderer.render_frame(time_ms)
            frame = frame.toarray(colorType=skia.kRGBA_8888_ColorType)

            process.stdin.write(frame.tobytes())

            if i % 30 == 0 and self.progress_callback:
                self.progress_callback(i + 1, total_frames)

        if not self._stop_event.is_set():
            self.progress_callback(total_frames, total_frames)

    def _render_cpu(
        self, process: subprocess.Popen, engine: StateEngine, total_frames: int
    ):
        cpu_count = max(1, os.cpu_count() - 1)

        self.log_callback(
            f"Using {cpu_count} CPU cores for rendering, total frames: {total_frames}",
            "INFO",
        )

        tasks = [int(i * 1000 / self.cfg.renderer.fps) for i in range(total_frames)]

        vo = engine.storyboard.video
        video_path = os.path.join(self.base_path, vo.filepath) if vo else None

        with multiprocessing.Pool(
            processes=cpu_count,
            initializer=init_worker,
            initargs=(
                engine,
                self.base_path,
                self.cfg.renderer.width,
                self.cfg.renderer.height,
                video_path,
                vo,
            ),
        ) as pool:
            result_iter = pool.imap(render_frame_worker, tasks, chunksize=10)

            for i, frame_bytes in enumerate(result_iter):
                if self._stop_event.is_set():
                    pool.terminate()
                    break

                process.stdin.write(frame_bytes)

                if i % 30 == 0 and self.progress_callback:
                    self.progress_callback(i + 1, total_frames)

        if not self._stop_event.is_set():
            self.progress_callback(total_frames, total_frames)

    def _merge_audio(self):
        if self.cfg.renderer.enable_audio and os.path.exists(self.audio_path):
            self.log_callback(f"Merging audio from {self.audio_path}", "INFO")
            output = self.cfg.path.output_path
            temp_output = output + ".temp.mp4"
            if os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(output):
                os.rename(output, temp_output)

            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_output,
                "-i",
                self.audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                output,
            ]

            result = subprocess.run(
                ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                self.log_callback(
                    f"Audio merge failed: {result.stderr.decode('utf-8', errors='replace')}",
                    "ERROR",
                )
                if os.path.exists(temp_output):
                    os.replace(temp_output, output)
                return

            if os.path.exists(temp_output):
                os.remove(temp_output)
            self.log_callback("Audio merged successfully.", "INFO")
        else:
            self.log_callback("No audio to merge or audio merging disabled.", "WARNING")
