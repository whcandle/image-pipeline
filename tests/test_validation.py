from __future__ import annotations

import pytest
from app.models.dtos import SafeArea


def test_safe_area_ok():
    sa = SafeArea(x=0.1, y=0.1, w=0.8, h=0.8)
    assert sa.x + sa.w <= 1.0


def test_safe_area_out_of_bounds():
    with pytest.raises(Exception):
        SafeArea(x=0.3, y=0.1, w=0.8, h=0.8)
