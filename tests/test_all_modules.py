"""
汇总测试：测试所有服务模块

运行所有模块的测试：
    pytest tests/test_all_modules.py -v

或者运行单个模块测试：
    pytest tests/test_template_resolver.py -v
    pytest tests/test_manifest_loader.py -v
    pytest tests/test_render_engine.py -v
    pytest tests/test_storage_manager.py -v
"""

import pytest


def test_template_resolver_basic():
    """
    测试 TemplateResolver 基本功能
    
    示例测试（需要实际的 HTTP 服务器提供模板下载）：
    """
    from app.services.template_resolver import TemplateResolver
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum="f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
    )
    
    # 验证初始化
    assert resolver.template_code == "tpl_001"
    assert resolver.version == "0.1.1"
    assert resolver.download_url == "http://127.0.0.1:9000/tpl_001_v0.1.1.zip"
    assert resolver.checksum == "f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d"
    
    # 注意：实际下载测试需要 HTTP 服务器，这里只测试结构
    # template_dir = resolver.resolve()
    # assert template_dir is not None  # 确保模板被正确下载和解压


def test_manifest_loader_basic():
    """测试 ManifestLoader 基本功能"""
    import tempfile
    import json
    from pathlib import Path
    from app.services.manifest_loader import ManifestLoader
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试 manifest.json
        manifest_data = {
            "outputWidth": 1800,
            "outputHeight": 1200,
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        }
        
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        # 测试加载
        loader = ManifestLoader(tmpdir)
        loaded_manifest = loader.load()
        
        assert loaded_manifest is not None
        assert loaded_manifest["outputWidth"] == 1800
        assert loaded_manifest["outputHeight"] == 1200


def test_render_engine_basic():
    """测试 RenderEngine 基本功能"""
    from PIL import Image
    from app.services.render_engine import RenderEngine
    
    manifest = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    engine = RenderEngine(manifest)
    test_image = Image.new("RGB", (500, 500), color=(255, 0, 0))
    
    result = engine.render(test_image.convert("RGBA"))
    
    assert result is not None
    assert result.size == (1800, 1200)


def test_storage_manager_basic():
    """测试 StorageManager 基本功能"""
    import tempfile
    from PIL import Image
    from app.services.storage_manager import StorageManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StorageManager(
            storage_base_path=tmpdir,
            public_base_url="http://localhost:9002"
        )
        
        test_image = Image.new("RGB", (100, 100), color=(255, 0, 0))
        url = manager.store(test_image, "test.jpg")
        
        assert url is not None
        assert url.startswith("http://localhost:9002")
        assert "files" in url
