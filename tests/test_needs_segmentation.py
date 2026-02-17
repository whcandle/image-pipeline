"""
测试 needs_segmentation 判定逻辑

测试用例：
1. source=raw：needs_cutout=false，流程正常
2. source=cutout 但 rules.enabled=false：needs_segmentation=false，仍走 raw 模式
3. source=cutout 且 rules.enabled=true：needs_segmentation=true
4. 多个 photos，其中一个 source=cutout：needs_cutout=true
"""

import json
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_template_dir_raw():
    """创建临时模板目录，source=raw"""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        
        # 创建 manifest.json（source=raw）
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
                        "source": "raw",  # raw 模式
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
        
        # 创建 assets 目录和背景图
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        
        # 创建背景图
        bg_image = Image.new("RGB", (1024, 1024), color=(0, 255, 0))
        bg_image.save(assets_dir / "bg.png", format="PNG")
        
        yield template_dir


@pytest.fixture
def temp_template_dir_cutout():
    """创建临时模板目录，source=cutout"""
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
        
        # 创建 assets 目录和背景图
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        
        # 创建背景图
        bg_image = Image.new("RGB", (1024, 1024), color=(0, 255, 0))
        bg_image.save(assets_dir / "bg.png", format="PNG")
        
        yield template_dir


@pytest.fixture
def temp_template_zip(temp_template_dir_raw, tmp_path):
    """创建模板 zip 文件（用于 raw 模式测试）"""
    zip_path = tmp_path / "template.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir_raw.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir_raw)
                zipf.write(file_path, arcname)
    
    return zip_path


@pytest.fixture
def temp_template_zip_cutout(temp_template_dir_cutout, tmp_path):
    """创建模板 zip 文件（用于 cutout 模式测试）"""
    zip_path = tmp_path / "template.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir_cutout.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir_cutout)
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
def mock_template_server(temp_template_zip, monkeypatch):
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
        
        with open(temp_template_zip, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)


@pytest.fixture
def mock_template_server_cutout(temp_template_zip_cutout, monkeypatch):
    """模拟模板下载服务器（cutout 模式）"""
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
        
        with open(temp_template_zip_cutout, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)


def test_needs_segmentation_source_raw(
    client, temp_template_dir_raw, temp_template_zip, temp_raw_image, mock_template_server, monkeypatch
):
    """
    测试场景 1：source=raw，needs_cutout=false，流程正常
    
    断言：
    - needs_cutout=false
    - seg_enabled=false（默认）
    - needs_segmentation=false
    - 流程正常完成（ok=true）
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_raw)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
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
    assert "NEEDS_CUTOUT" in notes
    assert notes["NEEDS_CUTOUT"]["details"]["value"] is False
    
    assert "SEG_ENABLED" in notes
    assert notes["SEG_ENABLED"]["details"]["value"] is False  # 默认 false
    
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is False


def test_needs_segmentation_source_cutout_disabled(
    client, temp_template_dir_cutout, temp_template_zip_cutout, temp_raw_image, mock_template_server_cutout, monkeypatch
):
    """
    测试场景 2：source=cutout 但 rules.enabled=false，needs_segmentation=false
    
    断言：
    - needs_cutout=true
    - seg_enabled=false（默认）
    - needs_segmentation=false（因为 seg_enabled=false）
    - 流程正常完成（仍走 raw 模式）
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip_cutout, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_cutout)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
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
    
    # 断言成功响应（即使 source=cutout，但 seg_enabled=false，所以仍走 raw 模式）
    assert data["ok"] is True
    
    # 提取 notes
    notes = {note["code"]: note for note in data["notes"]}
    
    # 断言判定结果
    assert "NEEDS_CUTOUT" in notes
    assert notes["NEEDS_CUTOUT"]["details"]["value"] is True
    
    assert "SEG_ENABLED" in notes
    assert notes["SEG_ENABLED"]["details"]["value"] is False  # 默认 false
    
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is False  # needs_cutout=true 但 seg_enabled=false


def test_needs_segmentation_source_cutout_enabled(
    client, temp_template_dir_cutout, temp_template_zip_cutout, temp_raw_image, mock_template_server_cutout, monkeypatch
):
    """
    测试场景 3：source=cutout 且 rules.enabled=true，needs_segmentation=true
    
    断言：
    - needs_cutout=true
    - seg_enabled=true（从 rules.json 读取）
    - needs_segmentation=true
    - 流程正常完成
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 创建 rules.json，设置 segmentation.enabled=true
    assets_dir = temp_template_dir_cutout / "assets"
    rules = {
        "segmentation.enabled": True,
        "segmentation.prefer": ["removebg"],
        "segmentation.timeoutMs": 5000
    }
    (assets_dir / "rules.json").write_text(
        json.dumps(rules, indent=2), encoding="utf-8"
    )
    
    # 重新创建 zip（包含 rules.json）
    zip_path = temp_template_zip_cutout.parent / "template_with_rules.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir_cutout.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir_cutout)
                zipf.write(file_path, arcname)
    
    # 计算 checksum
    with open(zip_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_cutout)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock 下载服务器返回新的 zip
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
        
        with open(zip_path, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)
    
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
    assert "NEEDS_CUTOUT" in notes
    assert notes["NEEDS_CUTOUT"]["details"]["value"] is True
    
    assert "SEG_ENABLED" in notes
    assert notes["SEG_ENABLED"]["details"]["value"] is True  # 从 rules.json 读取
    
    assert "NEEDS_SEGMENTATION" in notes
    assert notes["NEEDS_SEGMENTATION"]["details"]["value"] is True  # needs_cutout=true && seg_enabled=true


def test_needs_segmentation_multiple_photos(
    client, temp_template_dir_raw, temp_template_zip, temp_raw_image, mock_template_server, monkeypatch
):
    """
    测试场景 4：多个 photos，其中一个 source=cutout，needs_cutout=true
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 修改 manifest，添加多个 photos（一个 raw，一个 cutout）
    manifest_path = temp_template_dir_raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["compose"]["photos"].append({
        "id": "p2",
        "source": "cutout",  # 第二个 photo 是 cutout
        "x": 200,
        "y": 200,
        "w": 600,
        "h": 600,
        "fit": "cover",
        "z": 1
    })
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    
    # 重新创建 zip
    zip_path = temp_template_zip.parent / "template_multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir_raw.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir_raw)
                zipf.write(file_path, arcname)
    
    # 计算 checksum
    with open(zip_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir_raw)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock 下载服务器
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
        
        with open(zip_path, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)
    
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
    
    # 断言判定结果：因为有 cutout，所以 needs_cutout=true
    assert "NEEDS_CUTOUT" in notes
    assert notes["NEEDS_CUTOUT"]["details"]["value"] is True  # 因为有一个 photo source=cutout
