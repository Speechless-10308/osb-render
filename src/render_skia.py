from collections import defaultdict
import time
import skia
import math
from typing import Tuple, Dict
import numpy as np
from src.models import Layer, Origin, ObjectState, Vector2, VideoObject
from src.state_engine import StateEngine
from src.managers import AssetLoader
from src.video import VideoSource
import glfw


class SkiaRenderer:
    def __init__(
        self,
        engine: StateEngine,
        asset_loader: AssetLoader,
        width: int = 1280,
        height: int = 720,
        method: str = "linear",
        video_source: VideoSource | None = None,
        video_object: VideoObject | None = None,
    ):
        self.engine = engine
        self.asset_loader = asset_loader
        self.width = width
        self.height = height
        if method == "nearest":
            self.sample_method = skia.FilterMode.kNearest
        else:
            self.sample_method = skia.FilterMode.kLinear

        # Video support
        self.video_source = video_source
        self.video_object = video_object

        # cache for skia images
        self.image_cache: Dict[str, skia.Image] = {}

        self.scale_factor = self.height / 480.0
        self.offset_x = (self.width - 640 * self.scale_factor) / 2
        self.offset_y = 0

        self.layers = [
            self.engine.storyboard.background_layer,
            self.engine.storyboard.pass_layer,
            self.engine.storyboard.foreground_layer,
            self.engine.storyboard.overlay_layer,
        ]

        self.layer_names = [
            "Background",
            "Pass",
            "Foreground",
            "Overlay",
        ]

        self.layer_bucket = {
            "Background": defaultdict(list),
            "Fail": defaultdict(list),
            "Pass": defaultdict(list),
            "Foreground": defaultdict(list),
            "Overlay": defaultdict(list),
        }
        self._preprocess_buckets()

    def _preprocess_buckets(self, interval: int = 1000):
        layer_maps = {
            "Background": self.engine.storyboard.background_layer,
            "Fail": self.engine.storyboard.fail_layer,
            "Pass": self.engine.storyboard.pass_layer,
            "Foreground": self.engine.storyboard.foreground_layer,
            "Overlay": self.engine.storyboard.overlay_layer,
        }

        for layer, objects in layer_maps.items():
            for obj in objects:
                start = int(obj.life_start // interval)
                end = int(obj.life_end // interval)
                for bucket in range(start, end + 1):
                    self.layer_bucket[layer][bucket].append(obj)

    def _draw_video(self, canvas: skia.Canvas, time_ms: int):
        """Draw the current video frame, scaled to fill the output."""
        if self.video_source is None or self.video_object is None:
            return
        if not self.video_source.is_valid:
            return

        video_time = time_ms - self.video_object.start_time
        frame = self.video_source.get_frame(video_time)
        if frame is None:
            return

        # Scale video uniformly to cover the output (like object-fit: cover)
        vw, vh = self.video_source.width, self.video_source.height
        if vw <= 0 or vh <= 0:
            return

        cover_scale = max(self.width / vw, self.height / vh)
        draw_w = vw * cover_scale
        draw_h = vh * cover_scale

        # Centre the video on screen, then apply osu!-pixel offset
        cx = (self.width - draw_w) / 2 + self.video_object.x_offset * self.scale_factor
        cy = (self.height - draw_h) / 2 + self.video_object.y_offset * self.scale_factor

        paint = skia.Paint()
        paint.setAntiAlias(True)
        sampling = skia.SamplingOptions(skia.FilterMode.kLinear)

        dst_rect = skia.Rect(cx, cy, cx + draw_w, cy + draw_h)
        canvas.drawImageRect(frame, dst_rect, sampling, paint)

    def _draw_sprite(self, canvas: skia.Canvas, obj, state, img: skia.Image):
        """Draw a single sprite to the canvas with all transforms applied.

        Returns the screen-space (x, y) position of the sprite's origin,
        useful for subclasses that need to overlay debug info.
        """
        canvas.save()

        final_x = self.offset_x + state.position.x * self.scale_factor
        final_y = self.offset_y + state.position.y * self.scale_factor
        canvas.translate(final_x, final_y)

        # Handle rotation
        if abs(state.rotation) > 0.0001:
            degrees = math.degrees(state.rotation)
            canvas.rotate(degrees)

        # handle scaling and flipping
        sx = state.scale_vec.x * self.scale_factor
        sy = state.scale_vec.y * self.scale_factor

        if state.flip_h:
            sx = -sx
        if state.flip_v:
            sy = -sy

        canvas.scale(sx, sy)

        paint = skia.Paint()
        # Opacity (0-255)
        paint.setAlpha(int(state.opacity * 255))

        # Additive Blending (Additive)
        if state.additive:
            paint.setBlendMode(skia.BlendMode.kPlus)

        # Color Tinting
        # osu! uses Multiply mode for tinting
        if state.r != 255 or state.g != 255 or state.b != 255:
            color = skia.Color(int(state.r), int(state.g), int(state.b))
            paint.setColorFilter(
                skia.ColorFilters.Blend(color, skia.BlendMode.kModulate)
            )

        w, h = img.width(), img.height()

        # Geometric anti-aliasing on axis-aligned sprite edges causes
        # visible dark seams when two sprites share a boundary at a
        # sub-pixel screen coordinate — their independent AA coverage
        # doesn't sum to 100 %.  Since axis-aligned edges are already
        # straight pixel lines, geometric AA provides no benefit; the
        # texture's own alpha channel and bilinear sampling handle
        # in-content smoothness.  Only rotated sprites need AA for
        # their angled edges.
        # osu! itself uses MSAA at the framebuffer level (all
        # primitives resolved together), not per-sprite geometric AA,
        # so this also matches the client's visual output.
        has_rotation = abs(state.rotation) > 0.0001
        paint.setAntiAlias(has_rotation)

        sampling = skia.SamplingOptions(self.sample_method)
        ox, oy = self._get_origin_offset(w, h, obj.origin)

        # When flipped, the negative scale mirrors the local coordinate
        # system. Adjust the draw offset so the visual bounding box
        # stays on the same side of the origin — only the content flips.
        if state.flip_h:
            ox = w - ox
        if state.flip_v:
            oy = h - oy

        canvas.drawImage(img, -ox, -oy, sampling, paint)

        # Restore the coordinate system state for the next object
        canvas.restore()

        return final_x, final_y

    def draw_to_canvas(self, canvas: skia.Canvas, time_ms: int):
        """
        Draw the frame directly to a given Skia canvas
        """
        canvas.clear(skia.ColorBLACK)  # Black background

        # Video renders on the background layer, behind everything
        self._draw_video(canvas, time_ms)

        bucket_index = time_ms // 1000
        for layer in self.layer_names:
            active_objects = self.layer_bucket[layer][bucket_index]

            for obj in active_objects:
                state = self.engine.get_object_state(obj, time_ms)

                if not state or not state.visible or state.opacity < 0.001:
                    continue
                if abs(state.scale_vec.x) < 0.001 and abs(state.scale_vec.y) < 0.001:
                    continue

                img = self.asset_loader.load_image(state.image_path)
                if img is None:
                    continue

                self._draw_sprite(canvas, obj, state, img)

    def render_frame(self, time_ms: int) -> skia.Image:
        """
        The main rendering function using Skia
        """
        info = skia.ImageInfo.Make(
            self.width,
            self.height,
            skia.kRGBA_8888_ColorType,  # Use RGBA 8888
            skia.kPremul_AlphaType,
        )
        surface = skia.Surface.MakeRaster(info)
        with surface as canvas:
            self.draw_to_canvas(canvas, time_ms)

        return surface.makeImageSnapshot()

    def close(self):
        """Release resources (no-op for CPU renderer)."""
        pass

    def _get_origin_offset(self, w: int, h: int, origin: Origin) -> Tuple[float, float]:
        if origin == Origin.TopLeft:
            return 0, 0
        if origin == Origin.Centre:
            return w / 2, h / 2
        if origin == Origin.CentreLeft:
            return 0, h / 2
        if origin == Origin.TopRight:
            return w, 0
        if origin == Origin.BottomCentre:
            return w / 2, h
        if origin == Origin.TopCentre:
            return w / 2, 0
        if origin == Origin.CentreRight:
            return w, h / 2
        if origin == Origin.BottomLeft:
            return 0, h
        if origin == Origin.BottomRight:
            return w, h
        return w / 2, h / 2


class SkiaRendererGpu(SkiaRenderer):
    def __init__(
        self,
        engine: StateEngine,
        asset_loader: AssetLoader,
        width: int = 1280,
        height: int = 720,
        method: str = "linear",
        video_source: VideoSource | None = None,
        video_object: VideoObject | None = None,
    ):
        super().__init__(
            engine, asset_loader, width, height, method,
            video_source=video_source, video_object=video_object,
        )
        self._init_gl_context()

    def _init_gl_context(self):
        if not glfw.init():
            raise RuntimeError("GLFW initialization failed")

        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)

        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)

        self.window = glfw.create_window(
            self.width, self.height, "HiddenGL", None, None
        )

        if not self.window:
            glfw.terminate()
            raise RuntimeError("GLFW window creation failed")

        glfw.make_context_current(self.window)

        # Create Skia GPU context
        self.context = skia.GrDirectContext.MakeGL()
        if not self.context:
            raise RuntimeError("Failed to create Skia GrDirectContext")

        # Create Skia GPU surface
        image_info = skia.ImageInfo.Make(
            self.width,
            self.height,
            skia.kRGBA_8888_ColorType,
            skia.kPremul_AlphaType,
        )

        self.surface = skia.Surface.MakeRenderTarget(
            self.context,
            skia.Budgeted.kNo,
            image_info,
        )

        if not self.surface:
            raise RuntimeError("Failed to create Skia GPU surface")

    def render_frame(self, time_ms: int) -> skia.Image:
        """
        The main rendering function using Skia with GPU acceleration
        """
        glfw.make_context_current(self.window)

        with self.surface as canvas:
            self.draw_to_canvas(canvas, time_ms)

        self.context.flush()

        return self.surface.makeImageSnapshot()

    def __del__(self):
        self.close()

    def close(self):
        if hasattr(self, "window") and self.window:
            glfw.destroy_window(self.window)
            self.window = None
        if hasattr(self, "context") and self.context:
            self.context.abandonContext()
            self.context = None
