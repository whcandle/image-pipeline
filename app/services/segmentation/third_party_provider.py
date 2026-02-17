"""
Third-Party Segmentation Provider Module

This module handles calling third-party segmentation APIs (e.g., remove.bg)
to generate RGBA images with transparent backgrounds.
"""

import io
import httpx
from typing import Union, Dict, Any, Optional
from PIL import Image
from pathlib import Path


class SegmentationError(Exception):
    """Segmentation 处理失败的基础异常"""
    pass


class SegmentationProviderError(SegmentationError):
    """第三方 provider 调用失败"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_summary: Optional[str] = None):
        """
        Args:
            message: 错误消息
            status_code: HTTP 状态码（如果有）
            response_summary: 响应摘要（避免泄漏敏感信息）
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_summary = response_summary


class ThirdPartySegmentationProvider:
    """
    Provider for calling third-party segmentation APIs.
    
    Responsibilities:
    - Call third-party APIs (remove.bg, rembg, etc.) to remove backgrounds
    - Convert input images to RGBA format
    - Handle API authentication and errors
    """
    
    def __init__(self):
        """Initialize the provider."""
        pass
    
    def process(
        self,
        raw_image: Union[Image.Image, bytes, str, Path],
        execution_plan: Dict[str, Any],
    ) -> Image.Image:
        """
        调用第三方 API 进行抠图，返回 RGBA 图片。
        
        Args:
            raw_image: 原始图片（PIL Image、bytes、文件路径）
            execution_plan: Execution plan 字典，包含：
                - providerCode: provider 代码（如 "removebg"）
                - endpoint: API endpoint URL
                - auth: 认证信息（包含 apiKey）
                - timeoutMs: 超时时间（毫秒）
                - params: 额外参数（如 size、format 等）
                
        Returns:
            PIL Image (RGBA 模式，透明背景)
            
        Raises:
            SegmentationProviderError: 如果 API 调用失败
        """
        # 解析 execution plan
        provider_code = execution_plan.get("providerCode", "").lower()
        endpoint = execution_plan.get("endpoint", "")
        auth = execution_plan.get("auth", {})
        timeout_ms = execution_plan.get("timeoutMs", 6000)
        params = execution_plan.get("params", {})
        
        if not endpoint:
            raise SegmentationProviderError("Missing endpoint in execution plan")
        
        # 转换输入图片为 PIL Image
        input_image = self._prepare_input_image(raw_image)
        
        # 根据 provider 调用不同的处理方法
        if provider_code == "removebg":
            return self._call_removebg(input_image, endpoint, auth, timeout_ms, params)
        else:
            raise SegmentationProviderError(
                f"Unsupported provider: {provider_code}",
                response_summary=f"Provider {provider_code} is not implemented"
            )
    
    def _prepare_input_image(self, raw_image: Union[Image.Image, bytes, str, Path]) -> Image.Image:
        """
        将输入转换为 PIL Image。
        
        Args:
            raw_image: 原始图片（PIL Image、bytes、文件路径）
            
        Returns:
            PIL Image
        """
        if isinstance(raw_image, Image.Image):
            return raw_image
        elif isinstance(raw_image, bytes):
            return Image.open(io.BytesIO(raw_image))
        elif isinstance(raw_image, (str, Path)):
            return Image.open(raw_image)
        else:
            raise SegmentationProviderError(f"Unsupported image type: {type(raw_image)}")
    
    def _call_removebg(
        self,
        input_image: Image.Image,
        endpoint: str,
        auth: Dict[str, Any],
        timeout_ms: int,
        params: Dict[str, Any],
    ) -> Image.Image:
        """
        调用 remove.bg API。
        
        remove.bg API 规范：
        - 使用 multipart/form-data 上传
        - 字段名：image_file
        - Header: X-Api-Key
        - 返回：PNG bytes（RGBA）
        
        Args:
            input_image: PIL Image
            endpoint: remove.bg API endpoint
            auth: 认证信息（包含 apiKey）
            timeout_ms: 超时时间（毫秒）
            params: 额外参数（size、format 等）
            
        Returns:
            PIL Image (RGBA 模式)
        """
        # 获取 API key
        api_key = None
        if isinstance(auth, dict):
            api_key = auth.get("apiKey") or auth.get("api_key")
        
        if not api_key:
            raise SegmentationProviderError(
                "Missing API key for remove.bg",
                response_summary="API key not found in auth"
            )
        
        # 准备图片数据
        image_bytes = io.BytesIO()
        # remove.bg 接受多种格式，优先使用原始格式，否则转为 JPEG
        if input_image.format in ("JPEG", "PNG", "WEBP"):
            input_image.save(image_bytes, format=input_image.format)
        else:
            # 转换为 RGB（remove.bg 不支持某些格式）
            if input_image.mode != "RGB":
                input_image = input_image.convert("RGB")
            input_image.save(image_bytes, format="JPEG")
        
        image_bytes.seek(0)
        
        # 准备 multipart 数据
        files = {
            "image_file": ("image.jpg", image_bytes, "image/jpeg")
        }
        
        # 准备额外参数（size、format 等）
        data = {}
        if "size" in params:
            data["size"] = params["size"]
        if "format" in params:
            data["format"] = params["format"]
        
        # 准备 headers
        headers = {
            "X-Api-Key": api_key,
        }
        
        # 调用 API
        timeout_seconds = timeout_ms / 1000.0
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    endpoint,
                    files=files,
                    data=data,
                    headers=headers,
                )
                
                # 处理响应
                status_code = response.status_code
                if status_code == 200:
                    # 成功：返回 PNG bytes（RGBA）
                    result_image = Image.open(io.BytesIO(response.content))
                    # 确保是 RGBA 模式
                    if result_image.mode != "RGBA":
                        result_image = result_image.convert("RGBA")
                    return result_image
                else:
                    # 失败：提取错误信息
                    error_summary = f"HTTP {status_code}"  # 默认值
                    try:
                        error_summary = self._extract_error_summary(response)
                    except Exception:
                        pass  # 使用默认值
                    
                    # 直接抛出异常（确保 status_code 被设置）
                    raise SegmentationProviderError(
                        f"remove.bg API call failed: HTTP {status_code}",
                        status_code=status_code,
                        response_summary=error_summary,
                    )
        except SegmentationProviderError:
            # 重新抛出（已经设置了 status_code）
            raise
        except httpx.TimeoutException as e:
            raise SegmentationProviderError(
                f"remove.bg API call timeout: {timeout_ms}ms",
                status_code=None,
                response_summary="Request timeout",
            ) from e
        except httpx.HTTPStatusError as e:
            # HTTPStatusError 包含 response，可以提取状态码
            status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
            error_summary = self._extract_error_summary(e.response) if hasattr(e, 'response') and e.response else str(e)[:200]
            raise SegmentationProviderError(
                f"remove.bg API call failed: {e}",
                status_code=status_code,
                response_summary=error_summary,
            ) from e
        except httpx.HTTPError as e:
            raise SegmentationProviderError(
                f"remove.bg API call failed: {e}",
                status_code=None,
                response_summary=str(e)[:200],  # 限制长度
            ) from e
        except Exception as e:
            raise SegmentationProviderError(
                f"Unexpected error during remove.bg API call: {e}",
                status_code=None,
                response_summary=str(e)[:200],
            ) from e
    
    def _extract_error_summary(self, response: httpx.Response) -> str:
        """
        从响应中提取错误摘要（避免泄漏敏感信息）。
        
        Args:
            response: HTTP 响应对象
            
        Returns:
            错误摘要字符串
        """
        # 安全地提取状态码
        status_code = "unknown"
        try:
            if hasattr(response, 'status_code'):
                status_code = response.status_code
        except Exception:
            pass
        
        # 尝试解析 JSON 响应
        try:
            if hasattr(response, 'json'):
                error_data = response.json()
                if isinstance(error_data, dict):
                    # 提取常见错误字段
                    error_msg = (
                        error_data.get("error") or
                        error_data.get("message") or
                        error_data.get("errors") or
                        str(error_data)
                    )
                    # 限制长度，避免泄漏敏感信息
                    return str(error_msg)[:200]
        except Exception:
            pass
        
        # 如果无法解析 JSON，返回状态码和简短文本
        try:
            if hasattr(response, 'text') and response.text:
                text_preview = str(response.text)[:100]
            else:
                text_preview = ""
            return f"Status {status_code}: {text_preview}"
        except Exception:
            return f"Status {status_code}"
