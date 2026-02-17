"""
测试 PlatformClient 在 v2 process 中的集成

测试用例：
1. needs_segmentation=true 且 platform 正常：notes 有 SEG_RESOLVED_PROVIDER
2. needs_segmentation=true 但 platform 停掉：notes 有 SEG_RESOLVE_FAILED，流程不崩溃
3. needs_segmentation=false：不调用 resolve
"""

import json
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def temp_template_dir_cutout_with_rules():
    """创建临时模板目录，source=cutout，且有 rules.json（enabled=true）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        
        # 创建 manifest.json（source=cutout）
        manifest = {
            "manifestVersion": 1,
            "templateCode": "tpl_test",
            "versionSemver": "0.1.0",
            "output": {
                "width": 1024,
                "height": 1024,
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
                        "source": "cutout",  # cutout 模式
                        "x": 100,
                        "y": 100,
                        "w": 800,
                        "h": 800,
                        "fit": "cover",
                        "z": 0
                    }
                ],
                "stickers": []
            }
        }
        
        (template_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        
        # 创建 rules.json（segmentation.enabled=true）
        rules = {
            "segmentation": {
                "enabled": True,
                "prefer": ["removebg", "rembg"],
                "timeoutMs": 6000,
                "output": "rgba"
            }
        }
        (template_dir / "rules.json").write_text(
            json.dumps(rules, indent=2), encoding="utf-8"
        )
        
        # 创建 assets 目录和背景图
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        
        bg_image = Image.new("RGB", (1024, 1024), color=(0, 255, 0))
        bg_image.save(assets_dir / "bg.png", format="PNG")
        
        yield template_dir


@pytest.fixture
def temp_template_zip_cutout_with_rules(temp_template_dir_cutout_with_rules, tmp_path):
    """创建模板 zip 文件"""
    zip_path = tmp_path / "template.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir_cutout_with_rules.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir_cutout_with_rules)
                zipf.write(file_path, arcname)
    
    return zip_path


@pytest.fixture
def temp_raw_image(tmp_path):
    """创建临时原始图像"""
    raw_path = tmp_path / "raw.jpg"
    img = Image.new("RGB", (800, 1200), color=(255, 0, 0))
    img.save(raw_path, format="JPEG")
    return raw_path


@pytest.fixture
def mock_template_server_cutout_with_rules(temp_template_zip_cutout_with_rules, monkeypatch):
    """模拟模板下载服务器"""
    import requests
    
    def mock_get(url, **kwargs):
        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.status_code = 200
            
            def raise_for_status(self):
                pass
            
            def iter_content(self, chunk_size=8192):
                for i in range(0, len(self.content), chunk_size):
                    yield self.content[i:i + chunk_size]
        
        with open(temp_template_zip_cutout_with_rules, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)


def test_platform_resolve_success(
    client, temp_template_dir_cutout_with_rules, temp_template_zip_cutout_with_rules,
    temp_raw_image, mock_template_server_cutout_with_rules, monkeypatch
):
    """
    测试 platform resolve 成功
    
    断言：
    - needs_segmentation=true
    - notes 有 SEG_RESOLVED_PROVIDER
    - 流程正常完成（ok=true）
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip_cutout_with_rules, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_cutout_with_rules)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock PlatformClient.resolve() 成功
    from app.clients.platform_client import PlatformClient
    
    def mock_resolve_success(*args, **kwargs):
        return {
            "providerCode": "removebg",
            "endpoint": "https://api.remove.bg/v1.0/removebg",
            "timeoutMs": 6000,
        }
    
    monkeypatch.setattr(PlatformClient, "resolve", mock_resolve_success)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": checksum,
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # 断言成功响应
    assert data["ok"] is True
    
    # 提取 notes
    notes = {note["code"]: note for note in data["notes"]}
    
    # 断言判定结果
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is True
    
    # 断言 platform resolve 成功
    assert "SEG_RESOLVED_PROVIDER" in notes
    assert notes["SEG_RESOLVED_PROVIDER"]["details"]["providerCode"] == "removebg"
    assert "SEG_RESOLVE_FAILED" not in notes


def test_platform_resolve_failed(
    client, temp_template_dir_cutout_with_rules, temp_template_zip_cutout_with_rules,
    temp_raw_image, mock_template_server_cutout_with_rules, monkeypatch
):
    """
    测试 platform resolve 失败（platform 停掉）
    
    断言：
    - needs_segmentation=true
    - notes 有 SEG_RESOLVE_FAILED
    - 流程仍能完成（ok=true，不崩溃）
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    from app.clients.platform_client import PlatformClient, PlatformResolveError
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip_cutout_with_rules, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_cutout_with_rules)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock PlatformClient.resolve() 失败
    def mock_resolve_failed(*args, **kwargs):
        raise PlatformResolveError("Platform resolve API call failed: Connection refused")
    
    monkeypatch.setattr(PlatformClient, "resolve", mock_resolve_failed)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": checksum,
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    assert response.status_code == 200  # 不崩溃
    data = response.json()
    
    # 断言成功响应（即使 resolve 失败，流程仍能完成）
    assert data["ok"] is True
    
    # 提取 notes
    notes = {note["code"]: note for note in data["notes"]}
    
    # 断言判定结果
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is True
    
    # 断言 platform resolve 失败被记录
    assert "SEG_RESOLVE_FAILED" in notes
    assert notes["SEG_RESOLVE_FAILED"]["details"]["value"] is True
    assert "SEG_RESOLVED_PROVIDER" not in notes


def test_platform_resolve_not_called_when_not_needed(
    client, temp_template_dir_cutout_with_rules, temp_template_zip_cutout_with_rules,
    temp_raw_image, mock_template_server_cutout_with_rules, monkeypatch
):
    """
    测试 needs_segmentation=false 时不调用 resolve
    
    断言：
    - needs_segmentation=false（因为 rules.enabled=false）
    - 不调用 PlatformClient.resolve()
    - notes 没有 SEG_RESOLVED_PROVIDER 和 SEG_RESOLVE_FAILED
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    from app.clients.platform_client import PlatformClient
    
    # 修改 rules.json，设置 enabled=false
    rules = {
        "segmentation": {
            "enabled": False,  # 禁用
            "prefer": ["removebg"],
            "timeoutMs": 6000,
        }
    }
    (temp_template_dir_cutout_with_rules / "rules.json").write_text(
        json.dumps(rules, indent=2), encoding="utf-8"
    )
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip_cutout_with_rules, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_cutout_with_rules)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock PlatformClient.resolve() - 如果被调用，测试会失败
    resolve_called = []
    
    def mock_resolve_track(*args, **kwargs):
        resolve_called.append(True)
        return {"providerCode": "removebg"}
    
    monkeypatch.setattr(PlatformClient, "resolve", mock_resolve_track)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": checksum,
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # 断言成功响应
    assert data["ok"] is True
    
    # 提取 notes
    notes = {note["code"]: note for note in data["notes"]}
    
    # 断言判定结果
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is False
    
    # 断言 resolve 没有被调用
    assert len(resolve_called) == 0
    assert "SEG_RESOLVED_PROVIDER" not in notes
    assert "SEG_RESOLVE_FAILED" not in notes
