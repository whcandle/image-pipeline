from __future__ import annotations

from PIL import Image
from app.utils.image_ops import fit_or_fill


def test_fill_size():
    src = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    out = fit_or_fill(src, 200, 200, "FILL")
    assert out.size == (200, 200)


def test_fit_size():
    src = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    out = fit_or_fill(src, 200, 200, "FIT")
    assert out.size == (200, 200)
