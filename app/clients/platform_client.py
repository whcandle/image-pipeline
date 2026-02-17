"""
Platform Client Module

This module handles communication with the platform API for AI capabilities resolution.
"""

import httpx
from typing import Any, Dict, List, Optional
from app.config import settings


class PlatformResolveError(Exception):
    """Platform resolve API 调用失败"""
    pass


class PlatformClient:
    """
    Client for interacting with the platform API.
    
    Responsibilities:
    - Call platform resolve API to get execution plan
    - Handle errors gracefully (don't crash the main flow)
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout_ms: Optional[int] = None):
        """
        Initialize the PlatformClient.
        
        Args:
            base_url: Platform base URL (defaults to settings.PLATFORM_BASE_URL)
            timeout_ms: Request timeout in milliseconds (defaults to settings.PLATFORM_TIMEOUT_MS)
        """
        self.base_url = (base_url or settings.PLATFORM_BASE_URL).rstrip("/")
        self.timeout_ms = timeout_ms or settings.PLATFORM_TIMEOUT_MS
        self.timeout_seconds = self.timeout_ms / 1000.0
    
    def resolve(
        self,
        template_code: str,
        version_semver: str,
        prefer: List[str],
        timeout_ms: int,
        hint_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        调用 platform resolve API 获取 execution plan。
        
        Args:
            template_code: 模板代码
            version_semver: 模板版本号
            prefer: 优先使用的 provider 列表（从 rules.segmentation.prefer 获取）
            timeout_ms: 超时时间（从 rules.segmentation.timeoutMs 获取）
            hint_params: 提示参数（至少包含 output="rgba"）
            
        Returns:
            Execution plan 字典，包含：
            - providerCode: provider 代码
            - endpoint: API endpoint
            - timeoutMs: 超时时间
            
        Raises:
            PlatformResolveError: 如果 API 调用失败
        """
        url = f"{self.base_url}/api/v1/ai/resolve"
        
        # 构建请求体
        request_body = {
            "capability": "segmentation",
            "templateCode": template_code,
            "versionSemver": version_semver,
            "prefer": prefer,
            "constraints": {
                "timeoutMs": timeout_ms,
            },
            "hintParams": hint_params or {"output": "rgba"},
        }
        
        try:
            # 使用 httpx 发送请求
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=request_body)
                response.raise_for_status()
                result = response.json()
                
                # 解析 platform 返回的嵌套结构
                # 格式：{"success": true, "data": {"direct": {"providerCode": "...", "endpoint": "..."}}}
                if isinstance(result, dict) and "data" in result:
                    data = result["data"]
                    # 支持 direct 模式
                    if isinstance(data, dict) and "direct" in data:
                        direct = data["direct"]
                        # 提取 providerCode 和 endpoint
                        execution_plan = {
                            "providerCode": direct.get("providerCode", "unknown"),
                            "endpoint": direct.get("endpoint", ""),
                            "timeoutMs": direct.get("timeoutMs", timeout_ms),
                        }
                        # 如果有 auth 信息，也保留
                        if "auth" in direct:
                            execution_plan["auth"] = direct["auth"]
                        # 如果有 params，也保留
                        if "params" in direct:
                            execution_plan["params"] = direct["params"]
                        return execution_plan
                    # 如果 data 直接包含 providerCode 和 endpoint（兼容其他格式）
                    elif isinstance(data, dict) and "providerCode" in data:
                        return {
                            "providerCode": data.get("providerCode", "unknown"),
                            "endpoint": data.get("endpoint", ""),
                            "timeoutMs": data.get("timeoutMs", timeout_ms),
                        }
                
                # 如果已经是扁平结构（向后兼容）
                if isinstance(result, dict) and "providerCode" in result:
                    return result
                
                # 如果格式不符合预期，打印警告并返回默认值
                print(f"[PlatformClient] ⚠️ Unexpected response format: {result}")
                return {
                    "providerCode": "unknown",
                    "endpoint": "",
                    "timeoutMs": timeout_ms,
                }
        except httpx.HTTPError as e:
            raise PlatformResolveError(f"Platform resolve API call failed: {e}") from e
        except Exception as e:
            raise PlatformResolveError(f"Unexpected error during platform resolve: {e}") from e
