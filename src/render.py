import math
from typing import Tuple
from PIL import Image, ImageEnhance, ImageChops, ImageColor
from src.models import Layer, Origin, ObjectState, Vector2, Animation
from src.state_engine import StateEngine
from src.managers import AssetLoader


class StoryboardRenderer:
    def __init__(
        self,
        engine: StateEngine,
        asset_loader: AssetLoader,
        width: int = 1280,
        height: int = 720,
        fps: int = 60,
    ):
        self.engine = engine
        self.asset_loader = asset_loader
        self.width = width
        self.height = height
        self.background_color = (0, 0, 0, 255)  # Default black background

        self.scale_factor = self.height / 480.0

        self.offset_x = (self.width - 640 * self.scale_factor) / 2
        self.offset_y = 0

        self.layers = [
            self.engine.storyboard.background_layer,
            self.engine.storyboard.pass_layer,
            self.engine.storyboard.foreground_layer,
            self.engine.storyboard.overlay_layer,
        ]

    def _apply_transform(
        self, img: Image.Image, state: ObjectState, origin: Origin
    ) -> Tuple[Image.Image, int, int]:
        """
        Apply scale, rotate, color, opacity, and compute final position.
        Returns transformed image and its top-left position (x, y) on the canvas.
        """

        # Coloring
        if state.r != 255 or state.g != 255 or state.b != 255:
            color_overlay = Image.new(
                "RGBA", img.size, (int(state.r), int(state.g), int(state.b), 255)
            )
            a = img.getchannel("A")
            img = ImageChops.multiply(
                img.convert("RGB"), color_overlay.convert("RGB")
            ).convert("RGBA")
            img.putalpha(a)

        # Flipping
        if state.flip_h:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if state.flip_v:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        # Scaling
        scale_x = state.scale_vec.x * self.scale_factor
        scale_y = state.scale_vec.y * self.scale_factor

        if abs(scale_x) < 0.001 or abs(scale_y) < 0.001:
            return None, 0, 0  # Invisible due to zero scale

        new_width = int(img.width * scale_x)
        new_height = int(img.height * scale_y)

        if new_width <= 0 or new_height <= 0:
            return None, 0, 0  # Invisible due to zero size

        img = img.resize((new_width, new_height), resample=Image.BILINEAR)

        # Opacity
        if state.opacity < 1.0:
            alpha = img.getchannel("A")
            alpha = ImageEnhance.Brightness(alpha).enhance(state.opacity)
            img.putalpha(alpha)

        # Rotation. PIL rotates counter-clockwise, while osu! uses clockwise. Besides, the origin should be considered.
        ox, oy = get_origin_offset(img, origin)

        cx, cy = new_width / 2, new_height / 2

        if abs(state.rotation) > 0.001:
            theta = -state.rotation
            angle = math.degrees(theta)

            img = img.rotate(angle, resample=Image.BILINEAR, expand=True)

            # Compute new origin offset after rotation
            new_cx, new_cy = img.width / 2, img.height / 2

            dx = ox - cx
            dy = oy - cy

            cos_theta = math.cos(-theta)
            sin_theta = math.sin(-theta)

            new_dx = dx * cos_theta - dy * sin_theta
            new_dy = dx * sin_theta + dy * cos_theta

            ox = new_cx + new_dx
            oy = new_cy + new_dy

        # Final position on canvas
        final_x = int(self.offset_x + state.position.x * self.scale_factor - ox)
        final_y = int(self.offset_y + state.position.y * self.scale_factor - oy)

        return img, final_x, final_y

    def render_frame(self, time_ms: int) -> Image.Image:
        """
        Render a single frame at the given time (in milliseconds).
        """
        canvas = Image.new("RGBA", (self.width, self.height), self.background_color)

        for layer in self.layers:
            for idx, obj in enumerate(layer):
                state = self.engine.get_object_state(obj, time_ms)

                if not state or not state.visible:
                    continue  # Object is invisible at this time

                img = self.asset_loader.load_image(state.image_path, method="pil")

                if img == self.asset_loader.placeholder:
                    continue  # Image not found

                transformed_img, pos_x, pos_y = self._apply_transform(
                    img, state, obj.origin
                )

                if transformed_img is None:
                    continue  # Invisible due to zero scale

                if state.additive:
                    self._draw_additive(canvas, transformed_img, pos_x, pos_y)

                else:
                    canvas.alpha_composite(transformed_img, (pos_x, pos_y))

        return canvas

    def _draw_additive(self, canvas: Image.Image, img: Image.Image, x: int, y: int):
        cw, ch = canvas.size
        iw, ih = img.size

        left = max(x, 0)
        top = max(y, 0)
        right = min(x + iw, cw)
        bottom = min(y + ih, ch)

        if left >= right or top >= bottom:
            return  # No overlap

        crop_x = left - x
        crop_y = top - y
        cropped_img = img.crop(
            (crop_x, crop_y, crop_x + (right - left), crop_y + (bottom - top))
        )

        canvas_region = canvas.crop((left, top, right, bottom))

        r, g, b, a = cropped_img.split()
        img_rgb = cropped_img.convert("RGB")
        mask = a.convert("L")

        premultiplied = ImageChops.multiply(img_rgb, mask.convert("RGB"))

        bg_rgb = canvas_region.convert("RGB")
        added = ImageChops.add(bg_rgb, premultiplied)

        canvas.paste(added, (left, top))


def get_origin_offset(img: Image.Image, origin: Origin) -> tuple[float, float]:
    w, h = img.size
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
    if origin == Origin.Custom:
        return 0, 0  # WTH custom? As wiki said, use topleft
    if origin == Origin.CentreRight:
        return w, h / 2
    if origin == Origin.BottomLeft:
        return 0, h
    if origin == Origin.BottomRight:
        return w, h
    return w / 2, h / 2  # Default to Centre
