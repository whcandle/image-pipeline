"""
测试 ManifestLoader.validate_assets() 方法

验证：
1. 正常模板：所有资源文件存在，应该通过校验
2. 背景文件不存在：应该抛出 ManifestValidationError，错误信息包含路径
3. 贴纸文件不存在：应该抛出 ManifestValidationError，错误信息包含路径
"""

import pytest
import tempfile
import json
import zipfile
import io
import hashlib
from pathlib import Path
from unittest.mock import patch, Mock

from app.services.template_resolver import TemplateResolver
from app.services.manifest_loader import ManifestLoader, ManifestValidationError


def create_test_template_zip(manifest_data: dict, include_background: bool = True, include_stickers: bool = True) -> bytes:
    """创建测试模板 zip 文件"""
    zip_content = io.BytesIO()
    
    with zipfile.ZipFile(zip_content, "w") as zipf:
        # 写入 manifest.json
        zipf.writestr("manifest.json", json.dumps(manifest_data, indent=2, ensure_ascii=False))
        
        # 创建 assets 目录结构
        base_path = manifest_data.get("assets", {}).get("basePath", "assets")
        
        # 创建背景文件（如果需要）
        if include_background:
            background = manifest_data["compose"]["background"]
            bg_path = f"{base_path}/{background}"
            zipf.writestr(bg_path, b"fake background image data")
        
        # 创建贴纸文件（如果需要）
        if include_stickers and "stickers" in manifest_data["compose"]:
            for sticker in manifest_data["compose"]["stickers"]:
                src = sticker.get("src", "")
                if src.startswith("assets/") or src.startswith("assets\\"):
                    sticker_path = src
                else:
                    sticker_path = f"{base_path}/{src}"
                zipf.writestr(sticker_path, b"fake sticker image data")
    
    zip_content.seek(0)
    return zip_content.read()


@pytest.fixture
def temp_cache_dir():
    """创建临时缓存目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_validate_assets_normal_template(temp_cache_dir):
    """测试正常模板：所有资源文件存在，应该通过校验"""
    # 创建测试 manifest
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_001",
        "versionSemver": "0.1.1",
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "assets": {
            "basePath": "assets"
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 100,
                    "y": 200,
                    "w": 800,
                    "h": 900,
                    "fit": "cover"
                }
            ],
            "stickers": [
                {
                    "id": "s1",
                    "src": "assets/sticker1.png",
                    "x": 50,
                    "y": 50,
                    "w": 100,
                    "h": 100
                }
            ]
        }
    }
    
    # 创建 zip 文件
    zip_bytes = create_test_template_zip(manifest_data, include_background=True, include_stickers=True)
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    # 创建 TemplateResolver
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] 
        for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
    
    # 使用 ManifestLoader 加载 runtime spec
    loader = ManifestLoader(template_dir)
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 校验资源存在性（应该通过）
    loader.validate_assets(runtime_spec)
    
    # 验证结果
    assert Path(runtime_spec["background"]["path"]).exists()
    assert len(runtime_spec["photos"]) >= 1
    if runtime_spec.get("stickers"):
        for sticker in runtime_spec["stickers"]:
            assert Path(sticker["path"]).exists()


def test_validate_assets_missing_background(temp_cache_dir):
    """测试：背景文件不存在，应该早失败"""
    # 创建测试 manifest（背景文件名不存在）
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_001",
        "versionSemver": "0.1.1",
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "assets": {
            "basePath": "assets"
        },
        "compose": {
            "background": "nonexistent_bg.png",  # 不存在的文件名
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 100,
                    "y": 200,
                    "w": 800,
                    "h": 900
                }
            ]
        }
    }
    
    # 创建 zip 文件（不包含背景文件）
    zip_bytes = create_test_template_zip(manifest_data, include_background=False, include_stickers=False)
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    # 创建 TemplateResolver
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] 
        for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
    
    # 使用 ManifestLoader 加载 runtime spec
    loader = ManifestLoader(template_dir)
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 校验资源存在性（应该失败）
    with pytest.raises(ManifestValidationError) as exc_info:
        loader.validate_assets(runtime_spec)
    
    # 验证错误信息
    error_msg = str(exc_info.value)
    assert "Background file not found" in error_msg
    assert "nonexistent_bg.png" in error_msg


def test_validate_assets_missing_sticker(temp_cache_dir):
    """测试：贴纸文件不存在，应该早失败"""
    # 创建测试 manifest（贴纸文件名不存在）
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_001",
        "versionSemver": "0.1.1",
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "assets": {
            "basePath": "assets"
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 100,
                    "y": 200,
                    "w": 800,
                    "h": 900
                }
            ],
            "stickers": [
                {
                    "id": "s1",
                    "src": "assets/nonexistent_sticker.png",  # 不存在的文件名
                    "x": 50,
                    "y": 50,
                    "w": 100,
                    "h": 100
                }
            ]
        }
    }
    
    # 创建 zip 文件（包含背景，但不包含贴纸）
    zip_bytes = create_test_template_zip(manifest_data, include_background=True, include_stickers=False)
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    # 创建 TemplateResolver
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] 
        for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
    
    # 使用 ManifestLoader 加载 runtime spec
    loader = ManifestLoader(template_dir)
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 校验资源存在性（应该失败）
    with pytest.raises(ManifestValidationError) as exc_info:
        loader.validate_assets(runtime_spec)
    
    # 验证错误信息
    error_msg = str(exc_info.value)
    assert "Sticker file not found" in error_msg
    assert "nonexistent_sticker.png" in error_msg
    assert "s1" in error_msg  # sticker id


def test_validate_assets_multiple_stickers_one_missing(temp_cache_dir):
    """测试：多个贴纸，其中一个不存在，应该早失败"""
    # 创建测试 manifest（两个贴纸，一个存在，一个不存在）
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_001",
        "versionSemver": "0.1.1",
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "assets": {
            "basePath": "assets"
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 100,
                    "y": 200,
                    "w": 800,
                    "h": 900
                }
            ],
            "stickers": [
                {
                    "id": "s1",
                    "src": "assets/sticker1.png",  # 存在
                    "x": 50,
                    "y": 50,
                    "w": 100,
                    "h": 100
                },
                {
                    "id": "s2",
                    "src": "assets/nonexistent_sticker.png",  # 不存在
                    "x": 150,
                    "y": 150,
                    "w": 100,
                    "h": 100
                }
            ]
        }
    }
    
    # 创建 zip 文件（包含背景和一个贴纸，但不包含第二个贴纸）
    zip_bytes = create_test_template_zip(manifest_data, include_background=True, include_stickers=True)
    # 手动删除第二个贴纸
    zip_content = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_content, "r") as zipf:
        files_to_keep = [f for f in zipf.namelist() if not f.endswith("nonexistent_sticker.png")]
        new_zip_content = io.BytesIO()
        with zipfile.ZipFile(new_zip_content, "w") as new_zipf:
            for file_name in files_to_keep:
                new_zipf.writestr(file_name, zipf.read(file_name))
        new_zip_content.seek(0)
        zip_bytes = new_zip_content.read()
    
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    # 创建 TemplateResolver
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 下载
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] 
        for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
    
    # 使用 ManifestLoader 加载 runtime spec
    loader = ManifestLoader(template_dir)
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 校验资源存在性（应该失败）
    with pytest.raises(ManifestValidationError) as exc_info:
        loader.validate_assets(runtime_spec)
    
    # 验证错误信息
    error_msg = str(exc_info.value)
    assert "Sticker file not found" in error_msg
    assert "nonexistent_sticker.png" in error_msg
    assert "s2" in error_msg  # 第二个贴纸的 id
