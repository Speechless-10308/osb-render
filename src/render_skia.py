import skia
import math
from typing import Tuple, Dict
from PIL import Image
import numpy as np
from src.models import Layer, Origin, ObjectState, Vector2
from src.state_engine import StateEngine
from src.managers import AssetLoader


class SkiaRenderer:
    def __init__(
        self,
        engine: StateEngine,
        asset_loader: AssetLoader,
        width: int = 1280,
        height: int = 720,
    ):
        self.engine = engine
        self.asset_loader = asset_loader
        self.width = width
        self.height = height

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

    def _get_skia_image(self, path: str) -> skia.Image:
        """
        Got Skia Image from path
        """
        if path in self.image_cache:
            return self.image_cache[path]

        pil_img = self.asset_loader.load_image(path, method="pil")
        if pil_img == self.asset_loader.placeholder:
            return None  # Or handle placeholder

        # Ensure RGBA
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")

        # Convert to Skia Image
        # tobytes() is faster because it's a memory copy
        array = np.array(pil_img)
        skia_img = skia.Image.fromarray(array)

        # Cache it
        self.image_cache[path] = skia_img
        return skia_img

    def render_frame(self, time_ms: int) -> skia.Image:
        """
        The main rendering function using Skia
        """
        surface = skia.Surface(self.width, self.height)
        with surface as canvas:
            canvas.clear(skia.ColorBLACK)  # Black background

            for layer in self.layers:
                for obj in layer:
                    state = self.engine.get_object_state(obj, time_ms)

                    if not state or not state.visible or state.opacity < 0.001:
                        continue
                    if (
                        abs(state.scale_vec.x) < 0.001
                        and abs(state.scale_vec.y) < 0.001
                    ):
                        continue

                    img = self._get_skia_image(state.image_path)
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
                    sampling = skia.SamplingOptions(skia.FilterMode.kLinear)

                    w, h = img.width(), img.height()
                    ox, oy = self._get_origin_offset(w, h, obj.origin)

                    # Draw in the current transformed coordinate system
                    canvas.drawImage(img, -ox, -oy, sampling, paint)

                    # Restore the coordinate system state for the next object
                    canvas.restore()

        # Return snapshot
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
