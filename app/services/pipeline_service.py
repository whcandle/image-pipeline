from __future__ import annotations

from pathlib import Path
from PIL import Image

from app.models.dtos import PipelineRequest, StepInfo
from app.models.errors import ErrorCode
from app.services.storage_service import StorageService
from app.services.segment_service import SegmentService
from app.services.background_service import BackgroundService
from app.services.compose_service import ComposeService
from app.utils.timing import timed
from app.utils.logging import log_kv


class PipelineService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self.segmenter = SegmentService()
        self.bg = BackgroundService()
        self.composer = ComposeService()

    def run(self, req: PipelineRequest) -> dict:
        steps: list[StepInfo] = []

        # Validate rawPath exists
        raw_path = Path(req.rawPath)
        if not raw_path.exists() or not raw_path.is_file():
            return self._fail(
                req=req,
                steps=steps,
                code=ErrorCode.INVALID_INPUT,
                message="rawPath not found",
                detail={"rawPath": req.rawPath},
            )

        # Load raw image
        try:
            raw_img = Image.open(str(raw_path))
            raw_img.load()
        except Exception as e:
            return self._fail(
                req=req,
                steps=steps,
                code=ErrorCode.DECODE_FAILED,
                message="failed to decode raw image",
                detail={"rawPath": req.rawPath, "reason": str(e)},
            )

        # SEGMENT (MVP stub)
        try:
            with timed() as ms:
                person = self.segmenter.segment(raw_img, req.options)
            steps.append(StepInfo(name="SEGMENT", ms=ms()))
        except Exception as e:
            # 降级：用 raw 继续，但记录 step + 日志
            steps.append(StepInfo(name="SEGMENT", ms=0))
            person = raw_img.convert("RGBA")
            log_kv(
                "segment_failed_fallback",
                requestId=req.requestId,
                sessionId=req.sessionId,
                attemptIndex=req.attemptIndex,
                templateId=req.template.templateId,
                reason=str(e),
            )

        # BACKGROUND
        try:
            with timed() as ms:
                bg = self.bg.load_background(req.template, req.options)
            steps.append(StepInfo(name="BACKGROUND", ms=ms()))
        except Exception as e:
            # fallback gray background
            steps.append(StepInfo(name="BACKGROUND", ms=0))
            from PIL import Image as PILImage

            bg = PILImage.new("RGBA", (req.template.outputWidth, req.template.outputHeight), (200, 200, 200, 255))
            log_kv(
                "background_failed_fallback",
                requestId=req.requestId,
                sessionId=req.sessionId,
                attemptIndex=req.attemptIndex,
                templateId=req.template.templateId,
                reason=str(e),
            )

        # COMPOSE
        try:
            with timed() as ms:
                final_rgba = self.composer.compose(bg, person, req.template)
            steps.append(StepInfo(name="COMPOSE", ms=ms()))
        except Exception as e:
            return self._fail(
                req=req,
                steps=steps + [StepInfo(name="COMPOSE", ms=0)],
                code=ErrorCode.COMPOSE_FAILED,
                message="compose failed",
                detail={"reason": str(e)},
            )

        # STORE
        try:
            stored = self.storage.save_outputs(
                session_id=req.sessionId,
                attempt_index=req.attemptIndex,
                final_rgba=final_rgba,
                preview_width=req.output.previewWidth,
            )
        except Exception as e:
            return self._fail(
                req=req,
                steps=steps,
                code=ErrorCode.STORE_FAILED,
                message="store failed",
                detail={"reason": str(e)},
            )

        # log
        log_kv(
            "pipeline_ok",
            requestId=req.requestId,
            sessionId=req.sessionId,
            attemptIndex=req.attemptIndex,
            templateId=req.template.templateId,
            ok=True,
            steps=[s.model_dump() for s in steps],
            previewUrl=stored.preview_url,
            finalUrl=stored.final_url,
        )

        return {
            "ok": True,
            "previewUrl": stored.preview_url,
            "finalUrl": stored.final_url,
            "steps": [s.model_dump() for s in steps],
        }

    def _fail(self, req: PipelineRequest, steps: list[StepInfo], code: ErrorCode, message: str, detail: dict) -> dict:
        log_kv(
            "pipeline_failed",
            requestId=req.requestId,
            sessionId=req.sessionId,
            attemptIndex=req.attemptIndex,
            templateId=req.template.templateId,
            ok=False,
            errorCode=str(code),
            message=message,
            detail=detail,
            steps=[s.model_dump() for s in steps],
        )
        return {
            "ok": False,
            "steps": [s.model_dump() for s in steps],
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
            },
        }
