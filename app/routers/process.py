from fastapi import APIRouter, Request
from app.models.dtos import PipelineRequest
from app.models.errors import ErrorCode

router = APIRouter(prefix="/pipeline/v1", tags=["process"])


@router.post("/process")
def process(req: PipelineRequest, request: Request):
    try:
        pipeline_service = request.app.state.pipeline_service
        # PipelineService.run(req) 预计返回 Pydantic 模型（PipelineResponse）
        return pipeline_service.run(req).model_dump()
    except Exception as e:
        return {
            "ok": False,
            "steps": [],
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "internal error",
                "detail": {"reason": str(e)},
            },
        }
