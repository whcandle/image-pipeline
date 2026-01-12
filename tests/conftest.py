from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture()
def sample_images(tmp_path: Path):
    # create a raw image and template assets
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "0.jpg"
    Image.new("RGB", (1200, 800), (220, 50, 50)).save(raw_path)

    tpl_dir = tmp_path / "tpl_001"
    tpl_dir.mkdir(parents=True, exist_ok=True)

    bg_path = tpl_dir / "bg.jpg"
    Image.new("RGB", (1800, 1200), (50, 80, 200)).save(bg_path)

    overlay_path = tpl_dir / "overlay.png"
    overlay = Image.new("RGBA", (1800, 1200), (0, 0, 0, 0))
    # add a semi-transparent banner
    banner = Image.new("RGBA", (1800, 200), (0, 0, 0, 120))
    overlay.alpha_composite(banner, (0, 0))
    overlay.save(overlay_path)

    return {
        "raw_path": str(raw_path),
        "bg_path": str(bg_path),
        "overlay_path": str(overlay_path),
    }


@pytest.fixture(autouse=True)
def env_for_tests(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_data_dir))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:9002")
    yield
