from __future__ import annotations

from PIL import Image
from app.models.dtos import AiOptions
from app.utils.image_ops import ensure_rgba


class SegmentService:
    def segment(self, raw: Image.Image, options: AiOptions) -> Image.Image:
        """
        MVP：先不强制 rembg。
        - options.segmentation == "OFF" -> 直接返回 raw
        - "AUTO" -> 这里也先直接返回 raw（后续可替换为 rembg 输出透明人物）
        """
        return ensure_rgba(raw)
