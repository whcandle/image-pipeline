from pydantic import BaseModel, Field, model_validator
from typing import Any, Dict, List, Optional, Literal


class StepInfo(BaseModel):
    """处理步骤信息"""
    name: Literal["SEGMENT", "BACKGROUND", "COMPOSE", "TEMPLATE_RESOLVE", "MANIFEST_LOAD", "RENDER", "STORE"]
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


class PipelineV2Request(BaseModel):
    """
    模板驱动的 Pipeline v2 请求模型，对应 /pipeline/v2/process。
    
    支持两种方式提供原始图像：
    1. rawPath: 服务器本地文件路径（推荐用于服务间调用）
    2. raw: multipart 文件上传（用于客户端直接上传）
    """
    templateCode: str = Field(..., description="模板代码，如 'tpl_001'")
    versionSemver: str = Field(..., description="模板版本号，语义化版本格式，如 '0.1.0'")
    downloadUrl: str = Field(..., description="模板压缩包下载地址")
    checksumSha256: Optional[str] = Field(None, description="模板文件的 SHA256 校验和，用于验证文件完整性")
    rawPath: Optional[str] = Field(None, description="原始图像的服务器本地路径（与 raw 二选一）")
    # 注意：raw 文件上传需要在路由层使用 UploadFile，这里不定义在 DTO 中
    # 实际使用时，可以通过 FastAPI 的 File() 参数接收文件，然后与 DTO 合并处理


class NoteItem(BaseModel):
    """响应中的 notes 字段项"""
    code: str = Field(..., description="提示代码，如 'TEMPLATE_CACHED', 'WARN_LOW_QUALITY'")
    message: str = Field(..., description="提示消息")
    details: Optional[Dict[str, Any]] = Field(None, description="额外详情，可选")


class TimingInfo(BaseModel):
    """处理时间信息"""
    totalMs: int = Field(..., description="总处理时间（毫秒）")
    steps: List[StepInfo] = Field(default_factory=list, description="各步骤耗时")


class TemplateInfo(BaseModel):
    """模板信息"""
    templateCode: str
    versionSemver: str
    manifestVersion: int


class OutputUrls(BaseModel):
    """输出文件 URL"""
    previewUrl: Optional[str] = Field(None, description="预览图 URL")
    finalUrl: Optional[str] = Field(..., description="最终图 URL")


class PipelineV2ResponseOk(BaseModel):
    """
    成功响应模型。
    
    字段固定为：ok/jobId/template/outputs/timing/warnings/notes
    
    JSON 示例:
    {
      "ok": true,
      "jobId": "job_20240101_123456_abc123",
      "template": {
        "templateCode": "tpl_001",
        "versionSemver": "0.1.0",
        "manifestVersion": 1
      },
      "outputs": {
        "previewUrl": "http://localhost:9002/files/preview/job_20240101_123456_abc123/preview.png",
        "finalUrl": "http://localhost:9002/files/final/job_20240101_123456_abc123/final.png"
      },
      "timing": {
        "totalMs": 1234,
        "steps": [
          {"name": "TEMPLATE_RESOLVE", "ms": 450},
          {"name": "MANIFEST_LOAD", "ms": 12},
          {"name": "RENDER", "ms": 650},
          {"name": "STORE", "ms": 122}
        ]
      },
      "warnings": [],
      "notes": [
        {
          "code": "TEMPLATE_CACHED",
          "message": "Template was loaded from cache",
          "details": {"cachePath": "app/data/_templates/tpl_001/0.1.0/abc123..."}
        }
      ]
    }
    
    更多示例请参考: docs/v2_api_response_examples.md
    """
    ok: Literal[True] = Field(True, description="处理是否成功")
    jobId: str = Field(..., description="任务 ID，用于追踪和日志")
    template: TemplateInfo = Field(..., description="使用的模板信息")
    outputs: OutputUrls = Field(..., description="输出文件 URL")
    timing: TimingInfo = Field(..., description="处理时间信息")
    warnings: List[str] = Field(default_factory=list, description="警告消息列表")
    notes: List[NoteItem] = Field(default_factory=list, description="提示信息列表")


class PipelineV2ResponseError(BaseModel):
    """
    错误响应模型。
    
    字段固定为：ok/jobId/error/timing/notes
    
    JSON 示例:
    {
      "ok": false,
      "jobId": "job_20240101_123456_abc123",
      "error": {
        "code": "TEMPLATE_DOWNLOAD_ERROR",
        "message": "Failed to download template from URL",
        "detail": {
          "downloadUrl": "http://example.com/template.zip",
          "statusCode": 404
        }
      },
      "timing": {
        "totalMs": 150,
        "steps": [{"name": "TEMPLATE_RESOLVE", "ms": 150}]
      },
      "notes": [
        {
          "code": "ERROR_TEMPLATE_DOWNLOAD",
          "message": "Template download failed after 3 retries",
          "details": {"retryCount": 3}
        }
      ]
    }
    
    更多示例请参考: docs/v2_api_response_examples.md
    """
    ok: Literal[False] = Field(False, description="处理是否成功")
    jobId: Optional[str] = Field(None, description="任务 ID（如果已生成）")
    error: Dict[str, Any] = Field(..., description="错误信息，包含 code/message/detail")
    timing: Optional[TimingInfo] = Field(None, description="处理时间信息（如果已开始处理）")
    notes: List[NoteItem] = Field(default_factory=list, description="提示信息列表")


# 联合类型，用于类型提示
PipelineV2Response = PipelineV2ResponseOk | PipelineV2ResponseError