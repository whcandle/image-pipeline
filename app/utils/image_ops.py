from PIL import Image, ImageFilter
from typing import Tuple


def open_image(path: str) -> Image.Image:
    img = Image.open(path)
    # 统一转 RGBA，便于 alpha 合成
    return img.convert("RGBA")


def make_solid_bg(size: Tuple[int, int], color=(180, 180, 180, 255)) -> Image.Image:
    return Image.new("RGBA", size, color)


def fit_or_fill(src: Image.Image, target_w: int, target_h: int, mode: str) -> Image.Image:
    """mode: FIT(contain) / FILL(cover)"""
    sw, sh = src.size
    if sw <= 0 or sh <= 0:
        raise ValueError("invalid src size")

    scale_fit = min(target_w / sw, target_h / sh)
    scale_fill = max(target_w / sw, target_h / sh)
    scale = scale_fill if mode == "FILL" else scale_fit

    nw, nh = int(sw * scale), int(sh * scale)
    resized = src.resize((nw, nh), Image.LANCZOS)

    # canvas 目标尺寸
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    x = (target_w - nw) // 2
    y = (target_h - nh) // 2
    canvas.alpha_composite(resized, (x, y))
    if mode == "FILL":
        # FILL: 中心裁剪到 target
        return canvas.crop((0, 0, target_w, target_h))
    return canvas


def feather_alpha(img_rgba: Image.Image, feather_px: int) -> Image.Image:
    """对 alpha 通道做轻微羽化"""
    if feather_px <= 0:
        return img_rgba
    r, g, b, a = img_rgba.split()
    a2 = a.filter(ImageFilter.GaussianBlur(radius=feather_px / 2.0))
    return Image.merge("RGBA", (r, g, b, a2))
