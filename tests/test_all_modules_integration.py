"""
集成测试（legacy v1）

旧版集成测试依赖 outputWidth/outputHeight + safeArea 协议，
当前项目已迁移到 v2 模板协议（manifest + runtime_spec），
因此本文件整体跳过，避免与新实现冲突。
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Legacy v1 integration tests; superseded by v2 template-driven pipeline."
)

"""
集成测试：测试所有模块的协同工作

验证：
1. TemplateResolver + ManifestLoader + RenderEngine + StorageManager 的完整流程
2. 端到端的图像处理流程
"""

import pytest
import tempfile
import zipfile
import json
from pathlib import Path
from PIL import Image
from unittest.mock import patch, Mock
import io

from app.services.template_resolver import TemplateResolver
from app.services.manifest_loader import ManifestLoader
from app.services.render_engine import RenderEngine
from app.services.storage_manager import StorageManager


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_template_zip():
    """创建示例模板 zip 文件"""
    zip_content = io.BytesIO()
    
    # 创建 manifest.json
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    with zipfile.ZipFile(zip_content, "w") as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest_data, indent=2))
    
    zip_content.seek(0)
    return zip_content.read()


def test_full_pipeline_integration(temp_workspace, sample_template_zip):
    """测试完整的图像处理流程"""
    import hashlib
    
    # 1. TemplateResolver: 下载并解压模板
    checksum = hashlib.sha256(sample_template_zip).hexdigest()
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum=checksum,
        cache_dir=temp_workspace,
    )
    
    # Mock HTTP 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        sample_template_zip[i:i+chunk_size] 
        for i in range(0, len(sample_template_zip), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
        assert template_dir is not None
        assert Path(template_dir).exists()
    
    # 2. ManifestLoader: 加载 manifest.json
    loader = ManifestLoader(template_dir)
    manifest = loader.load()
    
    assert manifest["outputWidth"] == 1800
    assert manifest["outputHeight"] == 1200
    assert "safeArea" in manifest
    
    # 3. RenderEngine: 渲染图像
    sample_image = Image.new("RGB", (500, 500), color=(255, 0, 0))  # 红色
    engine = RenderEngine(manifest, template_dir=template_dir)
    rendered_image = engine.render(sample_image.convert("RGBA"))
    
    assert rendered_image.size == (1800, 1200)
    assert rendered_image.mode == "RGBA"
    
    # 4. StorageManager: 存储图像
    storage_dir = Path(temp_workspace) / "storage"
    manager = StorageManager(
        storage_base_path=str(storage_dir),
        public_base_url="http://localhost:9002"
    )
    
    final_url = manager.store(rendered_image, "final_output.jpg")
    
    assert final_url is not None
    assert final_url.startswith("http://localhost:9002")
    assert "final_output.jpg" in final_url or "jpg" in final_url.lower()
    
    # 验证文件已保存
    date_dirs = [d for d in storage_dir.iterdir() if d.is_dir()]
    assert len(date_dirs) > 0
    
    files = list(date_dirs[0].glob("*.jpg"))
    assert len(files) > 0


def test_pipeline_with_photos_config(temp_workspace):
    """测试使用 photos 配置的完整流程"""
    import hashlib
    
    # 创建包含 photos 配置的模板
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "photos": [
            {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
            {"x": 0.6, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FIT"},
        ],
    }
    
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, "w") as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest_data, indent=2))
    zip_content.seek(0)
    zip_bytes = zip_content.read()
    
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    resolver = TemplateResolver(
        template_code="tpl_002",
        version="1.0.0",
        download_url="http://127.0.0.1:9000/tpl_002_v1.0.0.zip",
        checksum=checksum,
        cache_dir=temp_workspace,
    )
    
    # Mock 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] 
        for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
    
    # 加载 manifest
    loader = ManifestLoader(template_dir)
    manifest = loader.load()
    assert len(manifest["photos"]) == 2
    
    # 渲染
    sample_image = Image.new("RGB", (500, 500), color=(0, 255, 0))  # 绿色
    engine = RenderEngine(manifest, template_dir=template_dir)
    rendered_image = engine.render(sample_image.convert("RGBA"))
    
    assert rendered_image.size == (1800, 1200)
    
    # 存储
    storage_dir = Path(temp_workspace) / "storage"
    manager = StorageManager(storage_base_path=str(storage_dir))
    final_url = manager.store(rendered_image)
    
    assert final_url is not None
