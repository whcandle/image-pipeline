from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from threading import Semaphore
from pathlib import Path

from app.config import settings
from app.utils.logging import log_event

from app.routers.health import router as health_router
from app.routers.process import router as process_router
from app.routers.test_segmentation import router as test_segmentation_router

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

# process_router 包含 v1 和 v2 两个版本的路由：
# - /pipeline/v1/process (原有接口，保持兼容)
# - /pipeline/v2/process (新增模板驱动接口)
# 路由定义在 app/routers/process.py 中
app.include_router(process_router)

# 测试路由（仅在开发环境使用）
# 注意：生产环境应该禁用或移除此路由
import os
if os.getenv("ENABLE_TEST_ROUTES", "").lower() in ("1", "true", "yes"):
    app.include_router(test_segmentation_router)

# ----------------------------
# static files
# ----------------------------
booth_root = Path(settings.BOOTH_DATA_DIR)
booth_root.mkdir(parents=True, exist_ok=True)
(booth_root / "preview").mkdir(parents=True, exist_ok=True)
(booth_root / "final").mkdir(parents=True, exist_ok=True)

# v2 本地模板输出：preview/final
app.mount(
    "/files/preview",
    StaticFiles(directory=str(booth_root / "preview")),
    name="files_preview",
)
app.mount(
    "/files/final",
    StaticFiles(directory=str(booth_root / "final")),
    name="files_final",
)

# 旧版接口仍然通过 /files 挂载 PIPELINE_DATA_DIR，保持兼容
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
