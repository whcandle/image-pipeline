import os
from pathlib import Path
from PIL import Image
from typing import Tuple


class StorageService:
    def __init__(self, data_dir: str, public_base_url: str):
        self.data_dir = Path(data_dir)
        self.public_base_url = public_base_url.rstrip("/")

        (self.data_dir / "preview").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "final").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "_debug").mkdir(parents=True, exist_ok=True)

    def _ensure_session_dir(self, kind: str, session_id: str) -> Path:
        p = self.data_dir / kind / session_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save_final_and_preview(
        self,
        session_id: str,
        attempt_index: int,
        final_rgba: Image.Image,
        preview_width: int,
    ) -> Tuple[str, str]:
        # final
        final_dir = self._ensure_session_dir("final", session_id)
        final_path = final_dir / f"{attempt_index}.jpg"

        rgb = final_rgba.convert("RGB")
        rgb.save(final_path, format="JPEG", quality=90)

        # preview
        preview_dir = self._ensure_session_dir("preview", session_id)
        preview_path = preview_dir / f"{attempt_index}.jpg"

        w, h = rgb.size
        if preview_width < w:
            ph = int(h * (preview_width / w))
            rgb_small = rgb.resize((preview_width, ph), Image.LANCZOS)
        else:
            rgb_small = rgb
        rgb_small.save(preview_path, format="JPEG", quality=80)

        preview_url = f"{self.public_base_url}/files/preview/{session_id}/{attempt_index}.jpg"
        final_url = f"{self.public_base_url}/files/final/{session_id}/{attempt_index}.jpg"
        return preview_url, final_url
