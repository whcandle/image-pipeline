from PIL import Image
from typing import Optional, Tuple

from app.utils.image_ops import feather_alpha


def _try_import_rembg():
    try:
        from rembg import remove  # type: ignore
        return remove
    except Exception:
        return None


_REMOVE = _try_import_rembg()


class SegmentService:
    def rembg_available(self) -> bool:
        return _REMOVE is not None

    def segment_auto(self, img_rgba: Image.Image, feather_px: int) -> Tuple[Image.Image, Optional[str]]:
        """
        返回 (person_rgba, err_reason)
        AUTO：rembg 可用就抠图，否则原图降级
        """
        if _REMOVE is None:
            return img_rgba, "rembg_not_available"

        try:
            out = _REMOVE(img_rgba)  # rembg 支持 PIL Image
            if not isinstance(out, Image.Image):
                out = Image.open(out).convert("RGBA")
            out = out.convert("RGBA")
            out = feather_alpha(out, feather_px)
            return out, None
        except Exception as e:
            # 降级：返回原图
            return img_rgba, f"rembg_failed:{e}"
