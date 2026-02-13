"""
测试 ManifestLoader 模块

验证：
1. manifest.json 加载功能
2. manifest 结构验证功能
3. 错误处理（文件不存在、格式错误等）
"""

import pytest
import tempfile
import json
from pathlib import Path
from app.services.manifest_loader import (
    ManifestLoader,
    ManifestNotFoundError,
    ManifestValidationError,
    ManifestParseError,
)


@pytest.fixture
def temp_template_dir():
    """创建临时模板目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_manifest_loader_init(temp_template_dir):
    """测试 ManifestLoader 初始化"""
    loader = ManifestLoader(temp_template_dir)
    
    assert loader.template_dir == Path(temp_template_dir)
    assert loader.manifest_path == Path(temp_template_dir) / "manifest.json"


def test_manifest_loader_load_valid_manifest(temp_template_dir):
    """测试加载有效的 manifest.json"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    manifest_path = Path(temp_template_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    
    loader = ManifestLoader(temp_template_dir)
    loaded_manifest = loader.load()
    
    assert loaded_manifest == manifest_data
    assert loaded_manifest["outputWidth"] == 1800
    assert loaded_manifest["outputHeight"] == 1200


def test_manifest_loader_load_with_photos(temp_template_dir):
    """测试加载包含 photos 配置的 manifest"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "photos": [
            {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
            {"x": 0.6, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FIT"},
        ],
    }
    
    manifest_path = Path(temp_template_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    
    loader = ManifestLoader(temp_template_dir)
    loaded_manifest = loader.load()
    
    assert len(loaded_manifest["photos"]) == 2
    assert loaded_manifest["photos"][0]["x"] == 0.1


def test_manifest_loader_load_with_stickers(temp_template_dir):
    """测试加载包含 stickers 配置的 manifest"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "stickers": [
            {"path": "sticker1.png", "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1},
        ],
    }
    
    manifest_path = Path(temp_template_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    
    loader = ManifestLoader(temp_template_dir)
    loaded_manifest = loader.load()
    
    assert len(loaded_manifest["stickers"]) == 1
    assert loaded_manifest["stickers"][0]["path"] == "sticker1.png"


def test_manifest_loader_not_found(temp_template_dir):
    """测试 manifest.json 不存在的情况"""
    loader = ManifestLoader(temp_template_dir)
    
    with pytest.raises(ManifestNotFoundError) as exc_info:
        loader.load()
    
    assert "manifest.json not found" in str(exc_info.value)


def test_manifest_loader_invalid_json(temp_template_dir):
    """测试无效的 JSON 格式"""
    manifest_path = Path(temp_template_dir) / "manifest.json"
    manifest_path.write_text("{ invalid json }", encoding="utf-8")
    
    loader = ManifestLoader(temp_template_dir)
    
    with pytest.raises(ManifestParseError):
        loader.load()


def test_manifest_loader_validate_safe_area_invalid():
    """测试 safeArea 验证失败的情况"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 1.0, "h": 1.0},  # w + x > 1
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        loader = ManifestLoader(tmpdir)
        
        with pytest.raises(ManifestValidationError) as exc_info:
            loader.load()
        
        assert "safeArea bounds exceed" in str(exc_info.value)


def test_manifest_loader_validate_photos_invalid():
    """测试 photos 配置验证失败的情况"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "photos": [
            {"x": 1.5, "y": 0.1, "w": 0.3, "h": 0.3},  # x > 1
        ],
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        loader = ManifestLoader(tmpdir)
        
        with pytest.raises(ManifestValidationError) as exc_info:
            loader.load()
        
        assert "photos" in str(exc_info.value).lower()


def test_manifest_loader_validate_stickers_missing_path():
    """测试 stickers 配置缺少 path 字段的情况"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "stickers": [
            {"x": 0.5, "y": 0.5},  # 缺少 path
        ],
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        loader = ManifestLoader(tmpdir)
        
        with pytest.raises(ManifestValidationError) as exc_info:
            loader.load()
        
        assert "path" in str(exc_info.value)


def test_manifest_loader_validate_output_size_invalid():
    """测试输出尺寸验证失败的情况"""
    manifest_data = {
        "outputWidth": -100,  # 无效的宽度
        "outputHeight": 1200,
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        loader = ManifestLoader(tmpdir)
        
        with pytest.raises(ManifestValidationError) as exc_info:
            loader.load()
        
        assert "outputWidth" in str(exc_info.value)


def test_manifest_loader_minimal_valid():
    """测试最小有效 manifest（只有输出尺寸）"""
    manifest_data = {
        "outputWidth": 1800,
        "outputHeight": 1200,
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        
        loader = ManifestLoader(tmpdir)
        loaded_manifest = loader.load()
        
        assert loaded_manifest["outputWidth"] == 1800
        assert loaded_manifest["outputHeight"] == 1200
