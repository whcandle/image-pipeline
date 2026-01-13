import os
from PIL import Image
from typing import Optional, Tuple

from app.utils.image_ops import make_solid_bg, open_image


class BackgroundService:
    def load_static_bg(self, bg_path: Optional[str], w: int, h: int) -> Image.Image:
        if bg_path and os.path.exists(bg_path):
            bg = open_image(bg_path)
            return bg.resize((w, h), Image.LANCZOS)
        # 缺失就用灰底
        return make_solid_bg((w, h))

    def generate_bg_stub(self, prompt: Optional[str], w: int, h: int) -> Tuple[Image.Image, Optional[str]]:
        """
        这里就是未来接"百炼/通义/OpenAI"的位置。
        MVP 先 stub：直接用灰底，并返回 reason。
        """
        return make_solid_bg((w, h)), "generate_not_implemented"
