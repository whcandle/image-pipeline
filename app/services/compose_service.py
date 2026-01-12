from __future__ import annotations

from pathlib import Path
from PIL import Image

from app.models.dtos import TemplateSpec
from app.utils.image_ops import fit_or_fill, alpha_over, ensure_rgba


class ComposeService:
    def compose(
        self,
        background: Image.Image,
        person_or_raw: Image.Image,
        template: TemplateSpec,
    ) -> Image.Image:
        bg = ensure_rgba(background)
        w, h = template.outputWidth, template.outputHeight
        if bg.size != (w, h):
            bg = bg.resize((w, h), Image.Resampling.LANCZOS)

        sa = template.safeArea
        sw = int(round(w * sa.w))
        sh = int(round(h * sa.h))
        sx = int(round(w * sa.x))
        sy = int(round(h * sa.y))

        placed = fit_or_fill(person_or_raw, sw, sh, template.cropMode)
        out = bg.copy()
        out.alpha_composite(ensure_rgba(placed), (sx, sy))

        # overlay optional
        if template.overlayPath:
            p = Path(template.overlayPath)
            if p.exists() and p.is_file():
                overlay = Image.open(str(p))
                overlay = ensure_rgba(overlay)
                out = alpha_over(out, overlay)

        return out
