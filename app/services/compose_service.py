import os
from PIL import Image
from typing import Optional

from app.utils.image_ops import fit_or_fill, open_image


class ComposeService:
    def compose(
        self,
        bg: Image.Image,
        person_rgba: Image.Image,
        overlay_path: Optional[str],
        safe_area: dict,
        crop_mode: str,
    ) -> Image.Image:
        W, H = bg.size
        canvas = bg.convert("RGBA")

        # safe area in pixels
        sx = int(W * safe_area["x"])
        sy = int(H * safe_area["y"])
        sw = int(W * safe_area["w"])
        sh = int(H * safe_area["h"])

        # resize person into safe area (FIT/FILL)
        placed = fit_or_fill(person_rgba, sw, sh, crop_mode)

        canvas.alpha_composite(placed, (sx, sy))

        # overlay optional
        if overlay_path and os.path.exists(overlay_path):
            ov = open_image(overlay_path).resize((W, H), Image.LANCZOS)
            canvas.alpha_composite(ov, (0, 0))

        return canvas
