import cv2
import numpy as np
import math
from src.models import Storyboard
from src.managers import AssetLoader
from src.state_engine import StateEngine


import cv2
import numpy as np
import math
from src.models import Storyboard, Layer
from src.managers import AssetLoader
from src.state_engine import StateEngine


class RendererSkia:
    def __init__(
        self,
        storyboard: Storyboard,
        state_engine: StateEngine,
        asset_manager: AssetLoader,
        width=1280,
        height=720,
    ):
        self.sb = storyboard
        self.engine = state_engine
        self.assets = asset_manager
        self.width = width
        self.height = height
        self.scale_factor = height / 480.0
        self.offset_x = (width - 640 * self.scale_factor) / 2
        self.offset_y = 0

    def render_frame(self, time_ms: int) -> np.ndarray:
        # 背景全黑，Alpha 255
        canvas = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        canvas[:, :, 3] = 255

        layers = [
            self.sb.background_layer,
            self.sb.pass_layer,
            self.sb.foreground_layer,
            self.sb.overlay_layer,
        ]

        for layer in layers:
            for obj in layer:
                if obj.life_start is not None and (
                    time_ms < obj.life_start or time_ms > obj.life_end
                ):
                    continue

                state = self.engine.get_object_state(obj, time_ms)
                # 兼容性处理：防止 None 或不可见
                if (
                    not state
                    or not state.visible
                    or (state.opacity is not None and state.opacity <= 0.001)
                ):
                    continue

                # 确保使用 state.image_path (处理动画)，如果为空则回退到 obj.filepath
                img_path = state.image_path if state.image_path else obj.filepath
                src_img = self.assets.load_image(img_path)

                if src_img is None or src_img.size == 0:
                    continue

                self.draw_object(canvas, src_img, state, obj.origin)

        return canvas

    def draw_object(self, canvas, img, state, origin_enum):
        h, w = img.shape[:2]

        # 1. 计算缩放
        # 这里保留你的逻辑：scale_vec 已经包含了所有缩放
        sx = state.scale_vec.x * self.scale_factor
        sy = state.scale_vec.y * self.scale_factor

        if state.flip_h:
            sx = -sx
        if state.flip_v:
            sy = -sy

        if abs(sx) < 0.001 or abs(sy) < 0.001:
            return

        # 2. 角度处理 (关键修复：必须取反，与 PIL 保持一致)
        # PIL: theta = -state.rotation
        theta = -state.rotation
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # 3. 原点与位置
        ox, oy = self.get_origin_coordinates(w, h, origin_enum)
        px = state.position.x * self.scale_factor + self.offset_x
        py = state.position.y * self.scale_factor + self.offset_y

        # 4. 构建矩阵 M
        # 对应 PIL 逻辑：
        # new_x = (x - ox) * sx * cos - (y - oy) * sy * sin + px
        # 展开后：
        # m00 = sx * cos
        # m01 = -sy * sin
        # tx = px - (ox * m00 + oy * m01)

        m00 = sx * cos_t
        m01 = -sy * sin_t
        m02 = px - (ox * m00 + oy * m01)

        m10 = sx * sin_t
        m11 = sy * cos_t
        m12 = py - (ox * m10 + oy * m11)

        M = np.array([[m00, m01, m02], [m10, m11, m12]], dtype=np.float32)

        # 5. ROI 计算与边界检查
        corners = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]]).T
        transformed_corners = M @ corners

        x_min = int(np.floor(transformed_corners[0].min()))
        x_max = int(np.ceil(transformed_corners[0].max()))
        y_min = int(np.floor(transformed_corners[1].min()))
        y_max = int(np.ceil(transformed_corners[1].max()))

        # 屏幕相交检测
        if x_min >= self.width or x_max <= 0 or y_min >= self.height or y_max <= 0:
            return

        # 计算在 Canvas 上的粘贴区域
        out_x = max(0, x_min)
        out_y = max(0, y_min)
        out_w = min(self.width, x_max) - out_x
        out_h = min(self.height, y_max) - out_y

        if out_w <= 0 or out_h <= 0:
            return

        # 6. 矩阵修正 (关键修复：修正 ROI 映射)
        # 我们要让原图中映射到 x_min 的点，现在映射到 0 (相对于 warp 输出图)
        # 如果我们只减去 out_x (即 max(0, x_min))，当 x_min < 0 时，我们减去了 0，
        # 导致矩阵依然映射到负坐标，图像左边被截断（黑边）。
        # 正确的做法是：减去 Canvas 粘贴点(out_x) 对应的 原始映射点(x_min) 之间的差值？
        # 其实最简单的理解是：Warp 的输出图像坐标系 (0,0) 应该对应 Canvas 的 (out_x, out_y)。
        # 而原始矩阵 M 映射到 Canvas 的 (x_min, y_min)。
        # 所以我们需要把矩阵整体平移：(out_x, out_y) -> (0, 0)
        # 也就是减去 out_x, out_y。

        # 修正：之前的解释有点绕，结论是你的代码 M_roi 减去 out_x 是对的。
        # 只要 x_min < 0，out_x = 0。M 映射到 -100。warp 里的 (0,0) 也就取到了 -100 的值。
        # 这里需要验证的是 opencv warpAffine 对负坐标的处理。
        # 实际上，warpAffine 是反向映射：dst(x,y) = src(inv(M) * (x,y))。
        # 我们的 M 是前向映射。OpenCV 内部会求逆。
        # 如果 M_roi[0,2] 依然是负数，OpenCV 会认为目标图像的 (0,0) 对应源图像的一个有效区域吗？
        # 不，M_roi 定义的是 源(0,0) -> 目标(tx, ty)。
        # 如果 tx = -100。目标图像的 (0,0) 对应源图像哪里？
        # x_dst = x_src * s - 100  =>  x_src = (x_dst + 100) / s.
        # 所以 x_dst=0 时，x_src 是正数。这是能取到值的。
        # 所以之前的 ROI 逻辑其实是可以工作的，问题核心还是在上面那个 theta 的符号。

        M_roi = M.copy()
        M_roi[0, 2] -= out_x
        M_roi[1, 2] -= out_y

        # 7. 渲染 Warp
        warped = cv2.warpAffine(
            img,
            M_roi,
            (out_w, out_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

        # 8. 混合 (Blending)
        bg_roi = canvas[out_y : out_y + out_h, out_x : out_x + out_w]

        # 转 float32
        fg = warped.astype(np.float32)
        bg = bg_roi.astype(np.float32)

        src_a = fg[:, :, 3] / 255.0

        if state.opacity < 1.0:
            src_a *= state.opacity

        if state.r != 255 or state.g != 255 or state.b != 255:
            tint = np.array([state.b, state.g, state.r], dtype=np.float32) / 255.0
            fg[:, :, :3] *= tint

        fg_premul = fg[:, :, :3] * src_a[:, :, np.newaxis]

        if state.additive:
            out_rgb = bg[:, :, :3] + fg_premul
            out_a = bg[:, :, 3]  # Additive 保持背景 Alpha
        else:
            # 标准混合
            inv_a = 1.0 - src_a[:, :, np.newaxis]
            out_rgb = fg_premul + bg[:, :, :3] * inv_a
            out_a = bg[:, :, 3]

        np.clip(out_rgb, 0, 255, out=out_rgb)

        canvas[out_y : out_y + out_h, out_x : out_x + out_w, :3] = out_rgb.astype(
            np.uint8
        )
        canvas[out_y : out_y + out_h, out_x : out_x + out_w, 3] = out_a.astype(np.uint8)

    def get_origin_coordinates(self, width, height, origin):
        # 保持你的 Origin 逻辑
        if origin.value == 0:
            return 0.0, 0.0
        if origin.value == 1:
            return width / 2, height / 2
        if origin.value == 2:
            return 0.0, height / 2
        if origin.value == 3:
            return width, 0.0
        if origin.value == 4:
            return width / 2, height
        if origin.value == 5:
            return width / 2, 0.0
        if origin.value == 7:
            return width, height / 2
        if origin.value == 8:
            return 0.0, height
        if origin.value == 9:
            return width, height
        return width / 2, height / 2
