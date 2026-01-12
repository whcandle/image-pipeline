from __future__ import annotations

from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    DECODE_FAILED = "DECODE_FAILED"
    SEGMENT_FAILED = "SEGMENT_FAILED"
    BACKGROUND_FAILED = "BACKGROUND_FAILED"
    COMPOSE_FAILED = "COMPOSE_FAILED"
    STORE_FAILED = "STORE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    detail: Dict[str, Any] = {}


class FailResponse(BaseModel):
    ok: bool = False
    steps: list[dict] = []
    error: ErrorBody
