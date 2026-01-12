from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.dtos import PipelineRequest
from app.models.errors import ErrorCode
from app.services.pipeline_service import PipelineService

router = APIRouter()
svc = PipelineService()


@router.post("/process")
def process(req: PipelineRequest):
    # 这里 req 已经过 Pydantic 校验；safeArea 越界会直接 422
    # 但我们希望错误码统一为 INVALID_INPUT（而不是 FastAPI 默认 422）
    try:
        result = svc.run(req)
        if result.get("ok") is True:
            return result
        # failed: map to 400
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_jsonable(result))
    except ValidationError as e:
        body = {
            "ok": False,
            "steps": [],
            "error": {
                "code": ErrorCode.INVALID_INPUT,
                "message": "validation failed",
                "detail": {"errors": e.errors()},
            },
        }
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=_jsonable(body))
    except Exception as e:
        body = {
            "ok": False,
            "steps": [],
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "internal error",
                "detail": {"reason": str(e)},
            },
        }
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=_jsonable(body))


def _jsonable(obj):
    # Enum -> value
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = _jsonable(v)
        return out
    if isinstance(obj, list):
        return [_jsonable(x) for x in obj]
    # pydantic/enum
    try:
        if hasattr(obj, "value"):
            return obj.value
    except Exception:
        pass
    return obj
