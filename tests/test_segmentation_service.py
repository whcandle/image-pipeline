"""
测试 SegmentationService 的降级逻辑

测试场景：
1. removebg 正常：notes 有 seg.provider=third_party
2. removebg endpoint 错误：notes 有 seg.fallback=rembg
3. rembg 禁用/异常：notes 有 seg.fallback=raw，仍能出图
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from app.services.segmentation.segmentation_service import SegmentationService
from app.services.segmentation.third_party_provider import SegmentationProviderError
from app.clients.platform_client import PlatformResolveError


@pytest.fixture
def sample_image():
    """创建测试图片"""
    img = Image.new("RGB", (800, 1200), color=(255, 0, 0))
    return img


@pytest.fixture
def rgba_result_image():
    """创建 RGBA 结果图片（模拟 remove.bg 返回）"""
    img = Image.new("RGBA", (800, 1200), color=(255, 0, 0, 255))
    # 添加一些透明区域（但主体区域足够大）
    pixels = img.load()
    # 中间区域不透明（主体）
    for x in range(200, 600):
        for y in range(200, 1000):
            pixels[x, y] = (255, 0, 0, 255)
    return img


@pytest.fixture
def rules():
    """创建规则配置"""
    return {
        "segmentation": {
            "enabled": True,
            "prefer": ["removebg", "rembg"],
            "timeoutMs": 6000,
            "fallback": "raw",
            "minSubjectAreaRatio": 0.08,
            "featherPx": 2,
        }
    }


def test_segmentation_third_party_success(sample_image, rgba_result_image, rules):
    """测试 third-party 成功场景"""
    # Mock platform resolve
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {"apiKey": "test_key"},
        "timeoutMs": 6000,
        "params": {},
    }
    
    # Mock platform client 和 third-party provider
    with patch('app.services.segmentation.segmentation_service.PlatformClient') as MockPlatformClient, \
         patch('app.services.segmentation.segmentation_service.ThirdPartySegmentationProvider') as MockThirdPartyProvider:
        
        mock_platform = MagicMock()
        mock_platform.resolve.return_value = execution_plan
        MockPlatformClient.return_value = mock_platform
        
        mock_provider = MagicMock()
        mock_provider.process.return_value = rgba_result_image
        MockThirdPartyProvider.return_value = mock_provider
        
        service = SegmentationService()
        cutout, notes = service.segment(
            raw_image=sample_image,
            template_code="tpl_001",
            version_semver="0.1.0",
            rules=rules,
        )
        
        # 验证结果
        assert cutout is not None
        assert cutout.mode == "RGBA"
        
        # 验证 notes
        note_codes = [n["code"] for n in notes]
        assert "seg.provider" in note_codes
        provider_note = next(n for n in notes if n["code"] == "seg.provider")
        assert provider_note["details"]["provider"] == "removebg"


def test_segmentation_fallback_to_rembg(sample_image, rules):
    """测试 third-party 失败，降级到 rembg"""
    # Mock platform resolve 成功
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {"apiKey": "test_key"},
        "timeoutMs": 6000,
        "params": {},
    }
    
    # Mock platform client 和 third-party provider
    with patch('app.services.segmentation.segmentation_service.PlatformClient') as MockPlatformClient, \
         patch('app.services.segmentation.segmentation_service.ThirdPartySegmentationProvider') as MockThirdPartyProvider, \
         patch('app.services.segmentation.segmentation_service.SegmentService') as MockSegmentService:
        
        mock_platform = MagicMock()
        mock_platform.resolve.return_value = execution_plan
        MockPlatformClient.return_value = mock_platform
        
        mock_provider = MagicMock()
        mock_provider.process.side_effect = SegmentationProviderError(
            "remove.bg API call failed: HTTP 401",
            status_code=401
        )
        MockThirdPartyProvider.return_value = mock_provider
        
        # Mock rembg 成功
        mock_rembg_service = MagicMock()
        rembg_result = Image.new("RGBA", (800, 1200), color=(255, 0, 0, 255))
        mock_rembg_service.segment_auto.return_value = (rembg_result, None)
        MockSegmentService.return_value = mock_rembg_service
        
        service = SegmentationService()
        cutout, notes = service.segment(
            raw_image=sample_image,
            template_code="tpl_001",
            version_semver="0.1.0",
            rules=rules,
        )
        
        # 验证结果（应该使用 rembg 的结果）
        assert cutout is not None
        assert cutout.mode == "RGBA"
        
        # 验证 notes
        note_codes = [n["code"] for n in notes]
        assert "SEG_THIRD_PARTY_FAIL" in note_codes
        assert "seg.fallback" in note_codes
        assert "seg.provider" in note_codes
        
        provider_note = next(n for n in notes if n["code"] == "seg.provider")
        assert provider_note["details"]["provider"] == "rembg"
        
        fallback_note = next(n for n in notes if n["code"] == "seg.fallback")
        assert fallback_note["details"]["fallback"] == "rembg"


def test_segmentation_fallback_to_raw(sample_image, rules):
    """测试 third-party 和 rembg 都失败，降级到 raw"""
    # Mock platform resolve 成功
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {"apiKey": "test_key"},
        "timeoutMs": 6000,
        "params": {},
    }
    
    # Mock platform client 和 third-party provider
    with patch('app.services.segmentation.segmentation_service.PlatformClient') as MockPlatformClient, \
         patch('app.services.segmentation.segmentation_service.ThirdPartySegmentationProvider') as MockThirdPartyProvider, \
         patch('app.services.segmentation.segmentation_service.SegmentService') as MockSegmentService:
        
        mock_platform = MagicMock()
        mock_platform.resolve.return_value = execution_plan
        MockPlatformClient.return_value = mock_platform
        
        mock_provider = MagicMock()
        mock_provider.process.side_effect = SegmentationProviderError(
            "remove.bg API call failed: HTTP 401",
            status_code=401
        )
        MockThirdPartyProvider.return_value = mock_provider
        
        # Mock rembg 也失败
        mock_rembg_service = MagicMock()
        mock_rembg_service.segment_auto.return_value = (sample_image, "rembg_failed: test error")
        MockSegmentService.return_value = mock_rembg_service
        
        service = SegmentationService()
        cutout, notes = service.segment(
            raw_image=sample_image,
            template_code="tpl_001",
            version_semver="0.1.0",
            rules=rules,
        )
        
        # 验证结果（应该返回原始图片）
        assert cutout is not None
        # 检查是否是同一个对象或相同尺寸
        assert cutout.size == sample_image.size
        
        # 验证 notes
        note_codes = [n["code"] for n in notes]
        assert "SEG_THIRD_PARTY_FAIL" in note_codes
        assert "SEG_REMBG_FAIL" in note_codes
        assert "seg.fallback" in note_codes
        assert "seg.provider" in note_codes
        
        provider_note = next(n for n in notes if n["code"] == "seg.provider")
        assert provider_note["details"]["provider"] == "raw"
        
        fallback_note = next(n for n in notes if n["code"] == "seg.fallback")
        assert fallback_note["details"]["fallback"] == "raw"


def test_segmentation_quality_check_fails(sample_image, rules):
    """测试质量检查失败，降级到 rembg"""
    # 创建一个质量很差的图片（几乎全透明）
    low_quality_image = Image.new("RGBA", (800, 1200), color=(0, 0, 0, 0))
    # 只有很小的主体区域
    pixels = low_quality_image.load()
    for x in range(0, 10):
        for y in range(0, 10):
            pixels[x, y] = (255, 0, 0, 255)
    
    # Mock platform resolve
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {"apiKey": "test_key"},
        "timeoutMs": 6000,
        "params": {},
    }
    
    # Mock platform client 和 third-party provider
    with patch('app.services.segmentation.segmentation_service.PlatformClient') as MockPlatformClient, \
         patch('app.services.segmentation.segmentation_service.ThirdPartySegmentationProvider') as MockThirdPartyProvider, \
         patch('app.services.segmentation.segmentation_service.SegmentService') as MockSegmentService:
        
        mock_platform = MagicMock()
        mock_platform.resolve.return_value = execution_plan
        MockPlatformClient.return_value = mock_platform
        
        mock_provider = MagicMock()
        mock_provider.process.return_value = low_quality_image
        MockThirdPartyProvider.return_value = mock_provider
        
        # Mock rembg 成功
        mock_rembg_service = MagicMock()
        rembg_result = Image.new("RGBA", (800, 1200), color=(255, 0, 0, 255))
        mock_rembg_service.segment_auto.return_value = (rembg_result, None)
        MockSegmentService.return_value = mock_rembg_service
        
        service = SegmentationService()
        cutout, notes = service.segment(
            raw_image=sample_image,
            template_code="tpl_001",
            version_semver="0.1.0",
            rules=rules,
        )
        
        # 验证结果（应该使用 rembg 的结果）
        assert cutout is not None
        assert cutout.mode == "RGBA"
        
        # 验证 notes 包含质量检查失败信息
        note_codes = [n["code"] for n in notes]
        assert "SEG_THIRD_PARTY_FAIL" in note_codes
        assert "seg.fallback" in note_codes
