"""
Debug test: render a single frame with sprite filepath labels, frame number,
and render time overlaid on the output image.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import skia
from src.models import Layer, Origin, ObjectState, Vector2
from src.state_engine import StateEngine
from src.parser import StoryboardParser
from src.render_skia import SkiaRenderer, SkiaRendererGpu
from src.managers import AssetLoader
from src.video import VideoSource


class DebugSkiaRenderer(SkiaRenderer):
    """Skia renderer that draws debug overlays: sprite filepaths, frame number, render time."""

    def __init__(
        self,
        engine,
        asset_loader,
        width=1920,
        height=1080,
        method="linear",
        video_source=None,
        video_object=None,
    ):
        super().__init__(
            engine,
            asset_loader,
            width,
            height,
            method,
            video_source=video_source,
            video_object=video_object,
        )
        self.render_time_ms = 0.0
        self._label_entries = []  # collected during _draw_sprite

        # Use a monospace font for legibility
        typeface = (
            skia.Typeface("Consolas") or skia.Typeface("Courier New") or skia.Typeface()
        )
        self.debug_font = skia.Font(typeface, 11)
        self.info_font = skia.Font(typeface, 16)

    def _draw_sprite(self, canvas, obj, state, img):
        """Draw the sprite and record its screen position for the debug overlay."""
        final_x, final_y = super()._draw_sprite(canvas, obj, state, img)
        self._label_entries.append((obj.filepath, final_x, final_y))

    def draw_to_canvas(self, canvas: skia.Canvas, time_ms: int):
        """Draw the frame via the base renderer, then overlay debug info."""
        self._label_entries = []
        super().draw_to_canvas(canvas, time_ms)
        self._draw_sprite_labels(canvas, self._label_entries)
        self._draw_frame_info(canvas, time_ms)

    def _draw_sprite_labels(self, canvas, entries):
        """Draw each sprite's filepath at its origin point on screen."""
        fg = skia.Paint(AntiAlias=True, Color=skia.ColorYELLOW)

        # Thin dark outline so yellow text stays readable on any background
        outline = skia.Paint()
        outline.setAntiAlias(True)
        outline.setColor(skia.ColorBLACK)
        outline.setStyle(skia.Paint.kStroke_Style)
        outline.setStrokeWidth(2.5)

        for filepath, x, y in entries:
            canvas.drawString(filepath, x + 2, y - 2, self.debug_font, outline)
            canvas.drawString(filepath, x, y - 4, self.debug_font, fg)

    def _draw_frame_info(self, canvas, time_ms):
        """Draw frame timestamp and render time at the top-left corner."""
        bg = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, 200))
        fg = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)

        frame_text = f"Frame: {time_ms} ms"
        time_text = f"Render time: {self.render_time_ms:.2f} ms"

        # Semi-transparent backdrop
        text_w = 320
        text_h = 50
        canvas.drawRect(skia.Rect(8, 8, 8 + text_w, 8 + text_h), bg)

        canvas.drawString(frame_text, 18, 30, self.info_font, fg)
        canvas.drawString(time_text, 18, 46, self.info_font, fg)

    def render_frame(self, time_ms: int) -> skia.Image:
        surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                self.width,
                self.height,
                skia.kRGBA_8888_ColorType,
                skia.kPremul_AlphaType,
            )
        )

        st = time.perf_counter()
        with surface as canvas:
            self.draw_to_canvas(canvas, time_ms)
        et = time.perf_counter()
        self.render_time_ms = (et - st) * 1000

        # Redraw time info now that render_time_ms is known
        with surface as canvas:
            self._draw_frame_info(canvas, time_ms)

        return surface.makeImageSnapshot()


class DebugSkiaRendererGpu(DebugSkiaRenderer):
    """GPU-accelerated variant of the debug renderer."""

    def __init__(
        self,
        engine,
        asset_loader,
        width=1920,
        height=1080,
        method="linear",
        video_source=None,
        video_object=None,
    ):
        super().__init__(
            engine,
            asset_loader,
            width,
            height,
            method,
            video_source=video_source,
            video_object=video_object,
        )
        self._init_gl_context()

    def _init_gl_context(self):
        import glfw

        if not glfw.init():
            raise RuntimeError("GLFW init failed")
        glfw.window_hint(glfw.VISIBLE, False)
        glfw.window_hint(glfw.RESIZABLE, False)
        self.window = glfw.create_window(self.width, self.height, "DebugGL", None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("GLFW window creation failed")
        glfw.make_context_current(self.window)
        self.context = skia.GrDirectContext.MakeGL()
        if not self.context:
            raise RuntimeError("Skia GrDirectContext creation failed")
        info = skia.ImageInfo.Make(
            self.width,
            self.height,
            skia.kRGBA_8888_ColorType,
            skia.kPremul_AlphaType,
        )
        self.surface = skia.Surface.MakeRenderTarget(
            self.context, skia.Budgeted.kNo, info
        )
        if not self.surface:
            raise RuntimeError("GPU surface creation failed")

    def render_frame(self, time_ms: int) -> skia.Image:
        import glfw

        glfw.make_context_current(self.window)

        st = time.perf_counter()
        with self.surface as canvas:
            self.draw_to_canvas(canvas, time_ms)
        et = time.perf_counter()
        self.render_time_ms = (et - st) * 1000

        # Redraw time info
        with self.surface as canvas:
            self._draw_frame_info(canvas, time_ms)

        self.context.flush()
        return self.surface.makeImageSnapshot()

    def __del__(self):
        self.close()

    def close(self):
        try:
            if hasattr(self, "window") and self.window:
                import glfw

                glfw.destroy_window(self.window)
                self.window = None
            if hasattr(self, "context") and self.context:
                self.context.abandonContext()
                self.context = None
        except Exception:
            pass


def test_debug_frame(
    time_ms: int,
    filepath: str,
    width: int = 1920,
    height: int = 1080,
    output: str = None,
    gpu: bool = False,
):
    import re

    basepath = os.path.dirname(filepath)

    print(f"Parsing: {filepath}")
    parser = StoryboardParser()
    storyboard = parser.parse(filepath)

    # If the input is a .osu file, also parse the companion .osb and merge.
    if filepath.lower().endswith(".osu"):
        filename = os.path.splitext(os.path.basename(filepath))[0]
        filename = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]\s*$", "", filename)
        osb_path = os.path.join(basepath, filename + ".osb")
        if os.path.exists(osb_path):
            print(f"Parsing companion .osb: {osb_path}")
            osb_parser = StoryboardParser()
            osb_storyboard = osb_parser.parse(osb_path)
            storyboard.merge(osb_storyboard)
        else:
            print(f"Companion .osb not found: {osb_path}")

    engine = StateEngine(storyboard)
    asset_loader = AssetLoader(base_path=basepath)

    # Initialise video source if the storyboard defines a video
    video_source = None
    video_obj = storyboard.video
    if video_obj is not None:
        video_path = os.path.join(basepath, video_obj.filepath)
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ffmpeg_path = os.path.join(
            proj_root, "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        )
        video_source = VideoSource(video_path, ffmpeg_path=ffmpeg_path)
        print(
            f"Video: {video_obj.filepath} ({video_source.width}x{video_source.height} {video_source.fps}fps {video_source.duration_ms}ms)"
        )

    cls = DebugSkiaRendererGpu if gpu else DebugSkiaRenderer
    renderer = cls(
        engine,
        asset_loader,
        width,
        height,
        video_source=video_source,
        video_object=video_obj,
    )

    print(
        f"Rendering at T={time_ms} ms ({width}x{height}, {'GPU' if gpu else 'CPU'}) ..."
    )
    img = renderer.render_frame(time_ms)

    if output is None:
        base = os.path.splitext(os.path.basename(filepath))[0]
        suffix = "_gpu" if gpu else ""
        output = f"debug_frame_T{time_ms}{suffix}.png"

    img.save(output)
    print(f"Saved -> {output}")
    print(f"Render time: {renderer.render_time_ms:.2f} ms")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Render a single debug frame with overlays"
    )
    ap.add_argument("osb_path", help="Path to .osb (or .osu) file")
    ap.add_argument(
        "-t", "--time", type=int, default=0, help="Timestamp in ms to render"
    )
    ap.add_argument("-W", "--width", type=int, default=1920)
    ap.add_argument("-H", "--height", type=int, default=1080)
    ap.add_argument("-o", "--output", default=None, help="Output PNG path")
    ap.add_argument("--gpu", action="store_true", help="Use GPU renderer")

    args = ap.parse_args()

    test_debug_frame(
        time_ms=args.time,
        filepath=args.osb_path,
        width=args.width,
        height=args.height,
        output=args.output,
        gpu=args.gpu,
    )
