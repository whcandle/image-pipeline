from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image

from app.config import load_settings


@dataclass(frozen=True)
class StoredOutputs:
    preview_path: Path
    final_path: Path
    preview_url: str
    final_url: str


class StorageService:
    def __init__(self) -> None:
        self.settings = load_settings()

    def _ensure_parent(self, p: Path) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)

    def build_paths(self, session_id: str, attempt_index: int) -> tuple[Path, Path]:
        preview = self.settings.data_dir / "preview" / session_id / f"{attempt_index}.jpg"
        final = self.settings.data_dir / "final" / session_id / f"{attempt_index}.jpg"
        return preview, final

    def build_urls(self, session_id: str, attempt_index: int) -> tuple[str, str]:
        base = self.settings.public_base_url.rstrip("/")
        preview_url = f"{base}/files/preview/{session_id}/{attempt_index}.jpg"
        final_url = f"{base}/files/final/{session_id}/{attempt_index}.jpg"
        return preview_url, final_url

    def save_jpeg(self, img: Image.Image, path: Path, quality: int) -> None:
        self._ensure_parent(path)
        img = img.convert("RGB")
        img.save(str(path), format="JPEG", quality=quality, optimize=True)

    def save_outputs(
        self,
        session_id: str,
        attempt_index: int,
        final_rgba: Image.Image,
        preview_width: int,
    ) -> StoredOutputs:
        preview_path, final_path = self.build_paths(session_id, attempt_index)
        preview_url, final_url = self.build_urls(session_id, attempt_index)

        # final
        self.save_jpeg(final_rgba, final_path, quality=90)

        # preview: resize by width
        fw, fh = final_rgba.size
        if preview_width <= 0:
            preview_width = min(900, fw)
        ph = int(round(fh * (preview_width / fw)))
        preview_img = final_rgba.resize((preview_width, ph), Image.Resampling.LANCZOS)
        self.save_jpeg(preview_img, preview_path, quality=80)

        return StoredOutputs(
            preview_path=preview_path,
            final_path=final_path,
            preview_url=preview_url,
            final_url=final_url,
        )
