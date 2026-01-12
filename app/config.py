from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    public_base_url: str
    max_segment_concurrency: int
    max_bg_concurrency: int


def load_settings() -> Settings:
    host = os.getenv("PIPELINE_HOST", "0.0.0.0")
    port = int(os.getenv("PIPELINE_PORT", "9002"))
    data_dir = Path(os.getenv("PIPELINE_DATA_DIR", "./app/data")).resolve()
    public_base_url = os.getenv("PUBLIC_BASE_URL", f"http://localhost:{port}").rstrip("/")

    max_segment = int(os.getenv("MAX_SEGMENT_CONCURRENCY", "1"))
    max_bg = int(os.getenv("MAX_BG_CONCURRENCY", "1"))

    return Settings(
        host=host,
        port=port,
        data_dir=data_dir,
        public_base_url=public_base_url,
        max_segment_concurrency=max_segment,
        max_bg_concurrency=max_bg,
    )
