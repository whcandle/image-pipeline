from __future__ import annotations

from pathlib import Path
from PIL import Image

from app.models.dtos import TemplateSpec, AiOptions
from app.utils.image_ops import ensure_rgba


class BackgroundService:
    def load_background(self, template: TemplateSpec, options: AiOptions) -> Image.Image:
        # MVP: 只做 STATIC；GENERATE 先 stub，fallback STATIC
        w, h = template.outputWidth, template.outputHeight

        bg_path = template.backgroundPath
        if bg_path:
            p = Path(bg_path)
            if p.exists() and p.is_file():
                try:
                    img = Image.open(str(p))
                    img = ensure_rgba(img).resize((w, h), Image.Resampling.LANCZOS)
                    return img
                except Exception:
                    pass

        # fallback: gray background
        return Image.new("RGBA", (w, h), (200, 200, 200, 255))
