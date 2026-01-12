from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


def _rembg_available() -> bool:
    # MVP: 先不依赖 rembg；后续你接 rembg 时改这里
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


@router.get("/health")
def health():
    return {
        "ok": True,
        "time": datetime.now(timezone.utc).isoformat(),
        "rembg": _rembg_available(),
    }
