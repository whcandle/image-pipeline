from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import load_settings
from app.routers.health import router as health_router
from app.routers.process import router as process_router
from app.utils.logging import log_kv


def create_app() -> FastAPI:
    settings = load_settings()

    app = FastAPI(title="Image Pipeline", version="0.1.0")

    # MVP: 允许跨域（设备端/本地调试方便）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure dirs
    (settings.data_dir / "preview").mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "final").mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "_debug").mkdir(parents=True, exist_ok=True)

    # /files -> serve local images
    app.mount(
        "/files",
        StaticFiles(directory=str(settings.data_dir), html=False),
        name="files",
    )

    app.include_router(health_router, prefix="/pipeline/v1", tags=["health"])
    app.include_router(process_router, prefix="/pipeline/v1", tags=["process"])

    log_kv(
        "pipeline_started",
        host=settings.host,
        port=settings.port,
        data_dir=str(Path(settings.data_dir)),
        public_base_url=settings.public_base_url,
    )

    return app


app = create_app()
