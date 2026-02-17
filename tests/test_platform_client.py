"""
测试 PlatformClient

测试用例：
1. resolve 成功：返回 execution plan
2. resolve 失败：抛出 PlatformResolveError
3. 网络超时：正确处理
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.clients.platform_client import PlatformClient, PlatformResolveError


def test_platform_client_resolve_success():
    """测试 resolve 成功"""
    # Mock httpx 响应
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "timeoutMs": 5000,
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = PlatformClient(base_url="http://localhost:9000", timeout_ms=5000)
        result = client.resolve(
            template_code="tpl_002",
            version_semver="0.1.2",
            prefer=["removebg", "rembg"],
            timeout_ms=6000,
            hint_params={"output": "rgba"},
        )
        
        assert result["providerCode"] == "removebg"
        assert result["endpoint"] == "https://api.remove.bg/v1.0/removebg"
        
        # 验证请求参数
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:9000/api/v1/ai/resolve"
        request_body = call_args[1]["json"]
        assert request_body["capability"] == "segmentation"
        assert request_body["templateCode"] == "tpl_002"
        assert request_body["versionSemver"] == "0.1.2"
        assert request_body["prefer"] == ["removebg", "rembg"]
        assert request_body["constraints"]["timeoutMs"] == 6000
        assert request_body["hintParams"]["output"] == "rgba"


def test_platform_client_resolve_http_error():
    """测试 resolve HTTP 错误"""
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client_class.return_value = mock_client
        
        client = PlatformClient(base_url="http://localhost:9000")
        
        with pytest.raises(PlatformResolveError) as exc_info:
            client.resolve(
                template_code="tpl_002",
                version_semver="0.1.2",
                prefer=["removebg"],
                timeout_ms=6000,
            )
        
        assert "Platform resolve API call failed" in str(exc_info.value)


def test_platform_client_resolve_timeout():
    """测试 resolve 超时"""
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value = mock_client
        
        client = PlatformClient(base_url="http://localhost:9000", timeout_ms=1000)
        
        with pytest.raises(PlatformResolveError) as exc_info:
            client.resolve(
                template_code="tpl_002",
                version_semver="0.1.2",
                prefer=["removebg"],
                timeout_ms=6000,
            )
        
        assert "Platform resolve API call failed" in str(exc_info.value)


def test_platform_client_resolve_unexpected_error():
    """测试 resolve 意外错误"""
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = ValueError("Unexpected error")
        mock_client_class.return_value = mock_client
        
        client = PlatformClient(base_url="http://localhost:9000")
        
        with pytest.raises(PlatformResolveError) as exc_info:
            client.resolve(
                template_code="tpl_002",
                version_semver="0.1.2",
                prefer=["removebg"],
                timeout_ms=6000,
            )
        
        assert "Unexpected error during platform resolve" in str(exc_info.value)
