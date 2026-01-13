from fastapi import APIRouter
from datetime import datetime, timezone

from app.services.segment_service import SegmentService

router = APIRouter(prefix="/pipeline/v1", tags=["health"])
_segmenter = SegmentService()


@router.get("/health")
def health():
    return {
        "ok": True,
        "time": datetime.now(timezone.utc).isoformat(),
        "rembg": _segmenter.rembg_available(),
    }
