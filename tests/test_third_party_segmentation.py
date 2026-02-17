"""
测试 ThirdPartySegmentationProvider

测试用例：
1. 成功调用 remove.bg API（mock）
2. API key 错误：抛出异常
3. 超时：抛出异常
4. 输入图片格式处理（PIL Image、bytes、文件路径）
"""

import io
import pytest
import httpx
from unittest.mock import patch, MagicMock
from PIL import Image
from pathlib import Path
from app.services.segmentation.third_party_provider import (
    ThirdPartySegmentationProvider,
    SegmentationProviderError,
)


@pytest.fixture
def sample_image():
    """创建测试图片"""
    img = Image.new("RGB", (800, 1200), color=(255, 0, 0))
    return img


@pytest.fixture
def rgba_result_image():
    """创建 RGBA 结果图片（模拟 remove.bg 返回）"""
    img = Image.new("RGBA", (800, 1200), color=(255, 0, 0, 255))
    # 添加一些透明区域
    pixels = img.load()
    for x in range(0, 100):
        for y in range(0, 100):
            pixels[x, y] = (0, 0, 0, 0)  # 透明
    return img


@pytest.fixture
def execution_plan():
    """创建 execution plan"""
    return {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {
            "type": "api_key",
            "apiKey": "test_api_key_12345",
        },
        "timeoutMs": 6000,
        "params": {
            "size": "auto",
            "format": "png",
        },
    }


def test_removebg_success(sample_image, rgba_result_image, execution_plan):
    """测试 remove.bg 成功调用"""
    # Mock httpx 响应
    rgba_bytes = io.BytesIO()
    rgba_result_image.save(rgba_bytes, format="PNG")
    rgba_bytes.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = rgba_bytes.getvalue()
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        result = provider.process(sample_image, execution_plan)
        
        # 验证结果
        assert result.mode == "RGBA"
        assert result.size == sample_image.size
        
        # 验证请求参数
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        assert "files" in call_kwargs
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["X-Api-Key"] == "test_api_key_12345"


def test_removebg_api_key_error(sample_image, execution_plan):
    """测试 API key 错误"""
    # Mock 401 响应
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = '{"errors": [{"title": "Unauthorized"}]}'
    mock_response.json.return_value = {"errors": [{"title": "Unauthorized"}]}
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        
        with pytest.raises(SegmentationProviderError) as exc_info:
            provider.process(sample_image, execution_plan)
        
        assert exc_info.value.status_code == 401
        assert "remove.bg API call failed" in str(exc_info.value)


def test_removebg_timeout(sample_image, execution_plan):
    """测试超时"""
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        
        with pytest.raises(SegmentationProviderError) as exc_info:
            provider.process(sample_image, execution_plan)
        
        assert "timeout" in str(exc_info.value).lower()


def test_removebg_missing_api_key(sample_image):
    """测试缺少 API key"""
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {},  # 没有 apiKey
        "timeoutMs": 6000,
    }
    
    provider = ThirdPartySegmentationProvider()
    
    with pytest.raises(SegmentationProviderError) as exc_info:
        provider.process(sample_image, execution_plan)
    
    assert "Missing API key" in str(exc_info.value)


def test_removebg_unsupported_provider(sample_image):
    """测试不支持的 provider"""
    execution_plan = {
        "providerCode": "unknown_provider",
        "endpoint": "https://api.example.com/removebg",
        "auth": {"apiKey": "test"},
        "timeoutMs": 6000,
    }
    
    provider = ThirdPartySegmentationProvider()
    
    with pytest.raises(SegmentationProviderError) as exc_info:
        provider.process(sample_image, execution_plan)
    
    assert "Unsupported provider" in str(exc_info.value)


def test_input_image_pil(sample_image, rgba_result_image, execution_plan):
    """测试输入为 PIL Image"""
    rgba_bytes = io.BytesIO()
    rgba_result_image.save(rgba_bytes, format="PNG")
    rgba_bytes.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = rgba_bytes.getvalue()
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        result = provider.process(sample_image, execution_plan)
        
        assert result.mode == "RGBA"


def test_input_image_bytes(sample_image, rgba_result_image, execution_plan):
    """测试输入为 bytes"""
    rgba_bytes = io.BytesIO()
    rgba_result_image.save(rgba_bytes, format="PNG")
    rgba_bytes.seek(0)
    
    # 准备输入 bytes
    input_bytes = io.BytesIO()
    sample_image.save(input_bytes, format="JPEG")
    input_bytes.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = rgba_bytes.getvalue()
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        result = provider.process(input_bytes.getvalue(), execution_plan)
        
        assert result.mode == "RGBA"


def test_input_image_path(tmp_path, sample_image, rgba_result_image, execution_plan):
    """测试输入为文件路径"""
    # 保存测试图片
    test_image_path = tmp_path / "test.jpg"
    sample_image.save(test_image_path, format="JPEG")
    
    rgba_bytes = io.BytesIO()
    rgba_result_image.save(rgba_bytes, format="PNG")
    rgba_bytes.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = rgba_bytes.getvalue()
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = ThirdPartySegmentationProvider()
        result = provider.process(test_image_path, execution_plan)
        
        assert result.mode == "RGBA"
