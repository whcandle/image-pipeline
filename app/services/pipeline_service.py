import os
from app.models.dtos import PipelineRequest, PipelineResponse, StepInfo
from app.models.errors import ErrorCode
from app.utils.timing import step_timer
from app.utils.logging import log_event
from app.utils.image_ops import open_image

from app.services.segment_service import SegmentService
from app.services.background_service import BackgroundService
from app.services.compose_service import ComposeService
from app.services.storage_service import StorageService


class PipelineService:
    def __init__(
        self,
        storage: StorageService,
        segmenter: SegmentService,
        bg_service: BackgroundService,
        composer: ComposeService,
        segment_sem,
        bg_sem,
    ):
        self.storage = storage
        self.segmenter = segmenter
        self.bg_service = bg_service
        self.composer = composer
        self.segment_sem = segment_sem
        self.bg_sem = bg_sem

    def run(self, req: PipelineRequest) -> PipelineResponse:
        steps = []

        opts = req.options
        out = req.output

        segmentation = (opts.segmentation if opts else "AUTO")
        feather_px = (opts.featherPx if opts else 0)
        bg_mode = (opts.bgMode if opts else "STATIC")

        preview_width = (out.previewWidth if out else 900)

        # validate raw
        if not os.path.exists(req.rawPath):
            return PipelineResponse(
                ok=False,
                steps=[],
                error={
                    "code": ErrorCode.INVALID_INPUT,
                    "message": "rawPath not found",
                    "detail": {"rawPath": req.rawPath},
                },
            )

        # load raw
        try:
            raw = open_image(req.rawPath)
        except Exception as e:
            return PipelineResponse(
                ok=False,
                steps=[],
                error={
                    "code": ErrorCode.DECODE_FAILED,
                    "message": "failed to decode raw image",
                    "detail": {"reason": str(e)},
                },
            )

        # SEGMENT (with semaphore gate for heavy work)
        with step_timer() as ms:
            person = raw
            seg_reason = None
            if segmentation in ("AUTO", "ON"):
                acquired = self.segment_sem.acquire(blocking=False)
                if not acquired:
                    # 闸门满：直接降级，不抠图（不阻塞）
                    person = raw
                    seg_reason = "segment_busy_downgrade"
                else:
                    try:
                        person, seg_reason = self.segmenter.segment_auto(raw, feather_px)
                    finally:
                        self.segment_sem.release()
            # OFF -> keep raw
            steps.append(StepInfo(name="SEGMENT", ms=ms()))
        # BACKGROUND
        with step_timer() as ms:
            W = req.template.outputWidth
            H = req.template.outputHeight

            bg = None
            bg_reason = None

            if bg_mode == "GENERATE":
                acquired = self.bg_sem.acquire(blocking=False)
                if not acquired:
                    bg = self.bg_service.load_static_bg(req.template.backgroundPath, W, H)
                    bg_reason = "bg_busy_fallback_static"
                else:
                    try:
                        bg, bg_reason = self.bg_service.generate_bg_stub(
                            opts.bgPrompt if opts else None, W, H
                        )
                        if bg_reason:
                            # fallback STATIC
                            bg = self.bg_service.load_static_bg(req.template.backgroundPath, W, H)
                    finally:
                        self.bg_sem.release()
            else:
                bg = self.bg_service.load_static_bg(req.template.backgroundPath, W, H)

            steps.append(StepInfo(name="BACKGROUND", ms=ms()))

        # COMPOSE
        with step_timer() as ms:
            try:
                final_rgba = self.composer.compose(
                    bg=bg,
                    person_rgba=person,
                    overlay_path=req.template.overlayPath,
                    safe_area=req.template.safeArea.model_dump(),
                    crop_mode=req.template.cropMode,
                )
            except Exception as e:
                return PipelineResponse(
                    ok=False,
                    steps=[*steps, StepInfo(name="COMPOSE", ms=ms())],
                    error={
                        "code": ErrorCode.COMPOSE_FAILED,
                        "message": "compose failed",
                        "detail": {"reason": str(e)},
                    },
                )
            steps.append(StepInfo(name="COMPOSE", ms=ms()))

        # STORE
        try:
            preview_url, final_url = self.storage.save_final_and_preview(
                session_id=req.sessionId,
                attempt_index=req.attemptIndex,
                final_rgba=final_rgba,
                preview_width=preview_width,
            )
        except Exception as e:
            return PipelineResponse(
                ok=False,
                steps=steps,
                error={
                    "code": ErrorCode.STORE_FAILED,
                    "message": "store failed",
                    "detail": {"reason": str(e)},
                },
            )

        log_event(
            "pipeline_process",
            requestId=req.requestId,
            sessionId=req.sessionId,
            attemptIndex=req.attemptIndex,
            templateId=req.template.templateId,
            ok=True,
            steps=[s.model_dump() for s in steps],
            segReason=seg_reason,
        )

        return PipelineResponse(ok=True, previewUrl=preview_url, finalUrl=final_url, steps=steps)
