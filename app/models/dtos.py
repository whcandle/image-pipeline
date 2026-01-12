from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


CropMode = Literal["FILL", "FIT"]
SegmentationMode = Literal["AUTO", "OFF"]
BgMode = Literal["STATIC", "GENERATE"]


class StepInfo(BaseModel):
    name: str
    ms: int


class SafeArea(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "SafeArea":
        if self.x + self.w > 1.0 + 1e-9:
            raise ValueError("safeArea x+w must be <= 1")
        if self.y + self.h > 1.0 + 1e-9:
            raise ValueError("safeArea y+h must be <= 1")
        return self


class TemplateSpec(BaseModel):
    templateId: str
    outputWidth: int = Field(gt=0)
    outputHeight: int = Field(gt=0)
    backgroundPath: Optional[str] = None
    overlayPath: Optional[str] = None
    safeArea: SafeArea
    cropMode: CropMode = "FILL"


class AiOptions(BaseModel):
    bgMode: BgMode = "STATIC"
    segmentation: SegmentationMode = "AUTO"
    featherPx: int = Field(default=6, ge=0, le=40)
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    bgPrompt: Optional[str] = None


class OutputOptions(BaseModel):
    previewWidth: int = Field(default=900, gt=0)
    finalWidth: int = Field(default=1800, gt=0)


class PipelineRequest(BaseModel):
    requestId: str
    sessionId: str
    attemptIndex: int = Field(ge=0)
    rawPath: str
    template: TemplateSpec
    options: AiOptions = AiOptions()
    output: OutputOptions = OutputOptions()


class PipelineResponse(BaseModel):
    ok: bool = True
    previewUrl: str
    finalUrl: str
    steps: List[StepInfo]
    error: Optional[Dict[str, Any]] = None  # success 时为 null/不返回也行
