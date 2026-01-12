from __future__ import annotations

from PIL import Image


def ensure_rgba(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        return img.convert("RGBA")
    return img


def ensure_rgb(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def fit_or_fill(
    src: Image.Image,
    target_w: int,
    target_h: int,
    mode: str,
) -> Image.Image:
    """
    mode:
      - FILL: cover + center crop
      - FIT:  contain + letterbox（透明背景）
    """
    src = ensure_rgba(src)
    sw, sh = src.size

    if sw <= 0 or sh <= 0:
        raise ValueError("invalid source image size")

    if mode == "FILL":
        scale = max(target_w / sw, target_h / sh)
        nw, nh = int(round(sw * scale)), int(round(sh * scale))
        resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
        # center crop
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))

    # FIT
    scale = min(target_w / sw, target_h / sh)
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    left = (target_w - nw) // 2
    top = (target_h - nh) // 2
    canvas.alpha_composite(resized, (left, top))
    return canvas


def alpha_over(base: Image.Image, overlay: Image.Image) -> Image.Image:
    base = ensure_rgba(base)
    overlay = ensure_rgba(overlay)
    if overlay.size != base.size:
        overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
    out = base.copy()
    out.alpha_composite(overlay, (0, 0))
    return out
