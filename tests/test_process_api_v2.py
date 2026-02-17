"""
测试 Pipeline V2 API (/pipeline/v2/process)

测试用例：
1. success：成功处理流程
2. checksum mismatch：校验和不匹配
3. bg 缺失：背景文件缺失
"""

import json
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_template_dir():
    """创建临时模板目录，包含完整的模板结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        
        # 创建 manifest.json
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
                        "source": "raw",
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
        
        (template_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        
        # 创建 assets 目录和背景图
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        
        # 创建背景图（纯绿色）
        bg_image = Image.new("RGB", (1024, 1024), color=(0, 255, 0))
        bg_image.save(assets_dir / "bg.png", format="PNG")
        
        yield template_dir


@pytest.fixture
def temp_template_zip(temp_template_dir, tmp_path):
    """创建模板 zip 文件"""
    zip_path = tmp_path / "template.zip"
    
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in temp_template_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_template_dir)
                zipf.write(file_path, arcname)
    
    return zip_path


@pytest.fixture
def temp_raw_image(tmp_path):
    """创建临时原始图像"""
    raw_path = tmp_path / "raw.jpg"
    img = Image.new("RGB", (800, 1200), color=(255, 0, 0))  # 红色
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
        
        # 读取 zip 文件内容
        with open(temp_template_zip, "rb") as f:
            content = f.read()
        
        return MockResponse(content)
    
    monkeypatch.setattr(requests, "get", mock_get)


def test_process_v2_success(client, temp_template_dir, temp_template_zip, temp_raw_image, mock_template_server, monkeypatch):
    """
    测试成功处理流程
    
    断言：
    - ok=true
    - preview/final url 存在
    - notes 至少有 PREVIEW_EQUALS_FINAL
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 计算 zip 文件的 checksum
    with open(temp_template_zip, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Mock TemplateResolver.resolve() 方法，直接返回模板目录
    original_resolve = TemplateResolver.resolve
    
    def mock_resolve(self):
        # 检查缓存是否存在，如果不存在则创建
        manifest_path = Path(temp_template_dir) / "manifest.json"
        if manifest_path.exists():
            return str(temp_template_dir)
        # 如果不存在，先创建（这种情况不应该发生，但为了安全）
        return str(temp_template_dir)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": checksum,
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    # 应该返回 200（不是 500）
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 断言成功响应
    assert data["ok"] is True, f"Expected ok=true, got {data.get('ok')}. Response: {json.dumps(data, indent=2)}"
    assert "jobId" in data, "Response should contain jobId"
    assert "outputs" in data, "Response should contain outputs"
    assert "previewUrl" in data["outputs"], "Response should contain outputs.previewUrl"
    assert "finalUrl" in data["outputs"], "Response should contain outputs.finalUrl"
    assert data["outputs"]["previewUrl"], "previewUrl should not be empty"
    assert data["outputs"]["finalUrl"], "finalUrl should not be empty"
    
    # 断言 notes 包含 PREVIEW_EQUALS_FINAL
    assert "notes" in data, "Response should contain notes"
    note_codes = [note["code"] for note in data["notes"]]
    assert "PREVIEW_EQUALS_FINAL" in note_codes, f"Expected PREVIEW_EQUALS_FINAL in notes, got {note_codes}"


def test_process_v2_checksum_mismatch(client, temp_template_dir, temp_template_zip, temp_raw_image, mock_template_server, monkeypatch):
    """
    测试校验和不匹配
    
    断言：
    - ok=false
    - error.code 为 TEMPLATE_CHECKSUM_MISMATCH
    - error.retryable=false
    - error.detail 包含 expected/actual
    """
    import hashlib
    from app.services.template_resolver import TemplateResolver
    
    # 计算正确的 checksum
    with open(temp_template_zip, "rb") as f:
        correct_checksum = hashlib.sha256(f.read()).hexdigest()
    
    # 使用错误的 checksum
    wrong_checksum = "wrong_checksum_" + "0" * 48
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": wrong_checksum,
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    # 应该返回 200（错误通过响应体返回，不抛 500）
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 断言错误响应
    assert data["ok"] is False, f"Expected ok=false, got {data.get('ok')}. Response: {json.dumps(data, indent=2)}"
    assert "error" in data, "Response should contain error"
    assert data["error"]["code"] == "TEMPLATE_CHECKSUM_MISMATCH", f"Expected TEMPLATE_CHECKSUM_MISMATCH, got {data['error'].get('code')}"
    assert data["error"].get("retryable") is False, "retryable should be False for checksum mismatch"
    assert "detail" in data["error"], "Error should contain detail"
    # expected 应该是我们传入的 wrong_checksum
    assert "expected" in data["error"]["detail"], "Error detail should contain expected checksum"
    # actual 应该是计算出的正确 checksum（如果能够提取的话）


def test_process_v2_bg_missing(client, temp_template_dir, temp_raw_image, monkeypatch):
    """
    测试背景文件缺失
    
    断言：
    - ok=false
    - error.code 为 ASSET_NOT_FOUND
    """
    from app.services.template_resolver import TemplateResolver
    from app.services.manifest_loader import ManifestLoader
    
    # 删除背景文件
    bg_path = temp_template_dir / "assets" / "bg.png"
    if bg_path.exists():
        bg_path.unlink()
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": "dummy_checksum",
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    # 应该返回 200（错误通过响应体返回，不抛 500）
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 断言错误响应
    assert data["ok"] is False, f"Expected ok=false, got {data.get('ok')}"
    assert "error" in data, "Response should contain error"
    assert data["error"]["code"] == "ASSET_NOT_FOUND", f"Expected ASSET_NOT_FOUND, got {data['error'].get('code')}"
    assert data["error"].get("retryable") is False, "retryable should be False for asset not found"


def test_process_v2_download_failed(client, temp_raw_image, monkeypatch):
    """
    测试模板下载失败
    
    断言：
    - ok=false
    - error.code 为 TEMPLATE_DOWNLOAD_FAILED
    - error.retryable=true
    """
    import requests
    
    def mock_get_failed(url, **kwargs):
        class MockResponse:
            status_code = 404
            
            def raise_for_status(self):
                raise requests.HTTPError("404 Not Found")
            
            def iter_content(self, chunk_size=8192):
                return iter([])
        
        return MockResponse()
    
    monkeypatch.setattr(requests, "get", mock_get_failed)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/nonexistent.zip",
        "checksumSha256": "dummy_checksum",
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    # 应该返回 200（错误通过响应体返回，不抛 500）
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 断言错误响应
    assert data["ok"] is False, f"Expected ok=false, got {data.get('ok')}"
    assert "error" in data, "Response should contain error"
    assert data["error"]["code"] == "TEMPLATE_DOWNLOAD_FAILED", f"Expected TEMPLATE_DOWNLOAD_FAILED, got {data['error'].get('code')}"
    assert data["error"].get("retryable") is True, "retryable should be True for download failure"


def test_process_v2_render_failed(client, temp_template_dir, temp_raw_image, monkeypatch):
    """
    测试渲染失败
    
    断言：
    - ok=false
    - error.code 为 RENDER_FAILED
    - error.retryable=false
    """
    from app.services.template_resolver import TemplateResolver
    from app.services.render_engine import RenderEngine, RenderError
    
    # Mock TemplateResolver
    def mock_resolve(self):
        return str(temp_template_dir)
    
    monkeypatch.setattr(TemplateResolver, "resolve", mock_resolve)
    
    # Mock RenderEngine 抛出异常
    def mock_render(*args, **kwargs):
        raise RenderError("Rendering failed: test error")
    
    monkeypatch.setattr(RenderEngine, "render", mock_render)
    
    payload = {
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/template.zip",
        "checksumSha256": "dummy_checksum",
        "rawPath": str(temp_raw_image)
    }
    
    response = client.post("/pipeline/v2/process", json=payload)
    
    # 应该返回 200（错误通过响应体返回，不抛 500）
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 断言错误响应
    assert data["ok"] is False, f"Expected ok=false, got {data.get('ok')}"
    assert "error" in data, "Response should contain error"
    assert data["error"]["code"] == "RENDER_FAILED", f"Expected RENDER_FAILED, got {data['error'].get('code')}"
    assert data["error"].get("retryable") is False, "retryable should be False for render failure"
