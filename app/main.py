from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from threading import Semaphore

from app.config import settings
from app.utils.logging import log_event

from app.routers.health import router as health_router
from app.routers.process import router as process_router

from app.services.storage_service import StorageService
from app.services.segment_service import SegmentService
from app.services.background_service import BackgroundService
from app.services.compose_service import ComposeService
from app.services.pipeline_service import PipelineService

app = FastAPI(title="Image Pipeline", version="0.1")

# ----------------------------
# services singletons
# ----------------------------
storage = StorageService(settings.PIPELINE_DATA_DIR, settings.PUBLIC_BASE_URL)
segmenter = SegmentService()
bg_service = BackgroundService()
composer = ComposeService()

segment_sem = Semaphore(settings.MAX_SEGMENT_CONCURRENCY)
bg_sem = Semaphore(settings.MAX_BG_CONCURRENCY)

pipeline_service = PipelineService(
    storage=storage,
    segmenter=segmenter,
    bg_service=bg_service,
    composer=composer,
    segment_sem=segment_sem,
    bg_sem=bg_sem,
)

# ✅ 关键：注入到 app.state，router 从 request.app.state 取
app.state.pipeline_service = pipeline_service

# ----------------------------
# routes
# ----------------------------
app.include_router(health_router)
app.include_router(process_router)

# ----------------------------
# static files
# ----------------------------
app.mount("/files", StaticFiles(directory=settings.PIPELINE_DATA_DIR), name="files")


@app.on_event("startup")
def on_startup():
    log_event(
        "pipeline_started",
        host=settings.PIPELINE_HOST,
        port=settings.PIPELINE_PORT,
        data_dir=settings.PIPELINE_DATA_DIR,
        public_base_url=settings.PUBLIC_BASE_URL,
    )
