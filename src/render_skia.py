from collections import defaultdict
import time
import skia
import math
from typing import Tuple, Dict
import numpy as np
from src.models import Layer, Origin, ObjectState, Vector2
from src.state_engine import StateEngine
from src.managers import AssetLoader
import glfw


class SkiaRenderer:
    def __init__(
        self,
        engine: StateEngine,
        asset_loader: AssetLoader,
        width: int = 1280,
        height: int = 720,
        method: str = "linear",
    ):
        self.engine = engine
        self.asset_loader = asset_loader
        self.width = width
        self.height = height
        if method == "nearest":
            self.sample_method = skia.FilterMode.kNearest
        else:
            self.sample_method = skia.FilterMode.kLinear

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

    def draw_to_canvas(self, canvas: skia.Canvas, time_ms: int):
        """
        Draw the frame directly to a given Skia canvas
        """
        canvas.clear(skia.ColorBLACK)  # Black background
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

                paint.setAntiAlias(True)
                sampling = skia.SamplingOptions(self.sample_method)

                w, h = img.width(), img.height()
                ox, oy = self._get_origin_offset(w, h, obj.origin)

                # Draw in the current transformed coordinate system
                canvas.drawImage(img, -ox, -oy, sampling, paint)

                # Restore the coordinate system state for the next object
                canvas.restore()

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
    ):
        super().__init__(engine, asset_loader, width, height, method)
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
        if hasattr(self, "window") and self.window:
            glfw.destroy_window(self.window)

        if hasattr(self, "context") and self.context:
            self.context.abandonContext()

        glfw.terminate()
