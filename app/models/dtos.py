from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, List, Optional, Literal


class StepInfo(BaseModel):
    name: Literal["SEGMENT", "BACKGROUND", "COMPOSE"]
    ms: int


class SafeArea(BaseModel):
    x: float
    y: float
    w: float
    h: float

    @model_validator(mode="after")
    def check_bounds(self):
        if not (0 <= self.x <= 1 and 0 <= self.y <= 1):
            raise ValueError("safeArea x/y must be in [0,1]")
        if not (0 < self.w <= 1 and 0 < self.h <= 1):
            raise ValueError("safeArea w/h must be in (0,1]")
        if self.x + self.w > 1 or self.y + self.h > 1:
            raise ValueError("safeArea x+w <= 1 and y+h <= 1")
        return self


class TemplateSpec(BaseModel):
    templateId: str
    outputWidth: int = Field(gt=0)
    outputHeight: int = Field(gt=0)
    backgroundPath: Optional[str] = None
    overlayPath: Optional[str] = None
    safeArea: SafeArea
    cropMode: Literal["FILL", "FIT"] = "FILL"


class AiOptions(BaseModel):
    bgMode: Literal["STATIC", "GENERATE"] = "STATIC"
    bgPrompt: Optional[str] = None
    segmentation: Literal["AUTO", "ON", "OFF"] = "AUTO"
    featherPx: int = Field(default=0, ge=0, le=40)
    strength: float = Field(default=0.6, ge=0.0, le=1.0)


class OutputOptions(BaseModel):
    previewWidth: int = Field(default=900, gt=0)
    finalWidth: int = Field(default=1800, gt=0)


class PipelineRequest(BaseModel):
    requestId: str
    sessionId: str
    attemptIndex: int = Field(ge=0)
    rawPath: str
    template: TemplateSpec
    options: Optional[AiOptions] = None
    output: Optional[OutputOptions] = None


class PipelineResponse(BaseModel):
    ok: bool
    previewUrl: Optional[str] = None
    finalUrl: Optional[str] = None
    steps: List[StepInfo] = []
    error: Optional[Dict[str, Any]] = None
