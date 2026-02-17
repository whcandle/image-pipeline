"""
临时测试 endpoint 用于测试 ThirdPartySegmentationProvider

注意：这是临时测试接口，生产环境应该移除或禁用。
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
import io
import tempfile
from pathlib import Path
from app.services.segmentation.third_party_provider import (
    ThirdPartySegmentationProvider,
    SegmentationProviderError,
)

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/segmentation/removebg")
async def test_removebg_segmentation(
    image: UploadFile = File(..., description="Input image (JPG/PNG)"),
    api_key: str = Form(..., description="remove.bg API key"),
    timeout_ms: int = Form(30000, description="Timeout in milliseconds"),
):
    """
    测试 remove.bg 抠图功能。
    
    输入：
    - image: 图片文件
    - api_key: remove.bg API key
    - timeout_ms: 超时时间（默认 30000ms）
    
    返回：
    - 透明背景的 PNG 图片
    """
    # 读取图片
    image_bytes = await image.read()
    input_image = Image.open(io.BytesIO(image_bytes))
    
    # 准备 execution plan
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {
            "type": "api_key",
            "apiKey": api_key,
        },
        "timeoutMs": timeout_ms,
        "params": {
            "size": "auto",
            "format": "png",
        },
    }
    
    # 调用 provider
    provider = ThirdPartySegmentationProvider()
    
    try:
        result_image = provider.process(input_image, execution_plan)
        
        # 保存到临时文件
        temp_dir = Path(tempfile.gettempdir()) / "image_pipeline_test"
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / f"cutout_{image.filename or 'test'}.png"
        result_image.save(output_path, format="PNG")
        
        return FileResponse(
            output_path,
            media_type="image/png",
            filename=f"cutout_{image.filename or 'test'}.png",
        )
    except SegmentationProviderError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail={
                "error": str(e),
                "status_code": e.status_code,
                "response_summary": e.response_summary,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Unexpected error: {e}"},
        )
