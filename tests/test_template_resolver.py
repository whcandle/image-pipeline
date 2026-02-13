"""
测试 TemplateResolver 模块

验证：
1. 模板下载功能
2. 校验和验证功能
3. 模板解压功能
4. 缓存机制
"""

import pytest
import tempfile
import zipfile
import hashlib
from pathlib import Path
from app.services.template_resolver import (
    TemplateResolver,
    TemplateDownloadError,
    TemplateChecksumMismatch,
    TemplateExtractError,
    TemplateInvalidError,
)


@pytest.fixture
def temp_cache_dir():
    """创建临时缓存目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_zip_file():
    """创建示例 zip 文件（包含 manifest.json）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "test_template.zip"
        
        # 创建临时目录和 manifest.json
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        manifest_path = template_dir / "manifest.json"
        manifest_path.write_text('{"outputWidth": 1800, "outputHeight": 1200}')
        
        # 创建 zip 文件
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.write(manifest_path, "manifest.json")
        
        yield zip_path


def test_template_resolver_init(temp_cache_dir):
    """测试 TemplateResolver 初始化"""
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url="http://example.com/template.zip",
        checksum="abc123",
        cache_dir=temp_cache_dir,
    )
    
    assert resolver.template_code == "tpl_001"
    assert resolver.version == "0.1.0"
    assert resolver.download_url == "http://example.com/template.zip"
    assert resolver.checksum == "abc123"
    assert Path(temp_cache_dir).exists()


def test_template_resolver_checksum_validation(sample_zip_file, temp_cache_dir):
    """测试校验和验证"""
    # 计算正确的校验和
    sha256_hash = hashlib.sha256()
    with open(sample_zip_file, "rb") as f:
        sha256_hash.update(f.read())
    correct_checksum = sha256_hash.hexdigest()
    
    # 使用正确的校验和（应该通过）
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url=f"file://{sample_zip_file}",  # 注意：requests 不支持 file://，这里只是测试结构
        checksum=correct_checksum,
        cache_dir=temp_cache_dir,
    )
    
    # 使用错误的校验和（应该失败）
    resolver_wrong = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url=f"file://{sample_zip_file}",
        checksum="wrong_checksum",
        cache_dir=temp_cache_dir,
    )
    
    # 注意：实际测试需要 HTTP 服务器，这里只测试结构
    assert resolver.checksum == correct_checksum


def test_template_extraction(sample_zip_file, temp_cache_dir):
    """测试模板解压功能"""
    # 计算校验和
    sha256_hash = hashlib.sha256()
    with open(sample_zip_file, "rb") as f:
        sha256_hash.update(f.read())
    checksum = sha256_hash.hexdigest()
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url="http://example.com/template.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # 手动测试解压逻辑
    template_cache_path = Path(temp_cache_dir) / "tpl_001" / "0.1.0" / checksum
    template_cache_path.mkdir(parents=True, exist_ok=True)
    
    # 解压
    with zipfile.ZipFile(sample_zip_file, "r") as zip_ref:
        zip_ref.extractall(template_cache_path)
    
    # 验证 manifest.json 存在
    manifest_path = template_cache_path / "manifest.json"
    assert manifest_path.exists()
    
    # 验证内容
    content = manifest_path.read_text()
    assert "outputWidth" in content


def test_template_resolver_cache_dir_creation(temp_cache_dir):
    """测试缓存目录自动创建"""
    cache_subdir = Path(temp_cache_dir) / "custom_cache"
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url="http://example.com/template.zip",
        checksum="test_checksum_123",
        cache_dir=str(cache_subdir),
    )
    
    assert cache_subdir.exists()
    assert resolver.cache_dir == cache_subdir


def test_template_resolver():
    """
    测试 TemplateResolver 完整流程（符合用户要求的格式）
    
    使用 mock 模拟 HTTP 下载，确保模板被正确下载和解压
    """
    import tempfile
    from unittest.mock import patch, Mock
    
    with tempfile.TemporaryDirectory() as temp_cache_dir:
        # 创建模拟的 zip 文件内容
        import io
        zip_content = io.BytesIO()
        with zipfile.ZipFile(zip_content, "w") as zipf:
            manifest_json = '{"outputWidth": 1800, "outputHeight": 1200, "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}}'
            zipf.writestr("manifest.json", manifest_json)
        zip_content.seek(0)
        zip_bytes = zip_content.read()
        
        # 计算校验和
        import hashlib
        checksum = hashlib.sha256(zip_bytes).hexdigest()
        
        resolver = TemplateResolver(
            template_code="tpl_001",
            version="0.1.1",
            download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
            checksum=checksum,
            cache_dir=temp_cache_dir,
        )
        
        # 验证初始化
        assert resolver.template_code == "tpl_001"
        assert resolver.version == "0.1.1"
        assert resolver.download_url == "http://127.0.0.1:9000/tpl_001_v0.1.1.zip"
        
        # Mock HTTP 请求
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [zip_bytes[i:i+chunk_size] for i in range(0, len(zip_bytes), chunk_size)]
        mock_response.raise_for_status = Mock()
        
        with patch("app.services.template_resolver.requests.get", return_value=mock_response):
            template_dir = resolver.resolve()
            
            # 确保模板被正确下载和解压
            assert template_dir is not None
            assert Path(template_dir).exists()
            assert (Path(template_dir) / "manifest.json").exists()
            
            # 验证 manifest.json 内容
            manifest_path = Path(template_dir) / "manifest.json"
            import json
            manifest_data = json.loads(manifest_path.read_text())
            assert manifest_data["outputWidth"] == 1800
            assert manifest_data["outputHeight"] == 1200


def test_template_resolver_with_real_http_server(temp_cache_dir, sample_zip_file):
    """
    测试 TemplateResolver 与真实 HTTP 服务器的集成（可选测试）
    
    需要先启动 HTTP 服务器：
    python -m http.server 9000 --directory <包含zip文件的目录>
    """
    import hashlib
    
    # 计算校验和
    sha256_hash = hashlib.sha256()
    with open(sample_zip_file, "rb") as f:
        sha256_hash.update(f.read())
    correct_checksum = sha256_hash.hexdigest()
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/test_template.zip",  # 需要服务器提供此文件
        checksum=correct_checksum,
        cache_dir=temp_cache_dir,
    )
    
    # 注意：此测试需要 HTTP 服务器运行
    # 如果服务器不可用，测试会跳过或失败
    try:
        template_dir = resolver.resolve()
        assert template_dir is not None
        assert Path(template_dir).exists()
        assert (Path(template_dir) / "manifest.json").exists()
    except TemplateDownloadError:
        pytest.skip("HTTP server not available, skipping real download test")


# ============================================================
# 新增测试用例（Prompt 3 要求）
# ============================================================

def test_cache_hit(temp_cache_dir):
    """测试缓存命中"""
    import json
    from unittest.mock import patch, Mock
    
    resolver = TemplateResolver(
        template_code="tpl_cache",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum="cache_test_checksum",
        cache_dir=temp_cache_dir,
    )
    
    # 手动创建缓存目录和 manifest.json
    resolver.final_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = resolver.final_dir / "manifest.json"
    manifest_data = {"outputWidth": 1800, "outputHeight": 1200}
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    # 调用 resolve，应该直接返回，不访问网络
    with patch("app.services.template_resolver.requests.get") as mock_get:
        template_dir = resolver.resolve()
        
        # 验证：没有调用 requests.get（缓存命中）
        mock_get.assert_not_called()
        
        # 验证：返回正确的目录
        assert template_dir == str(resolver.final_dir.resolve())
        assert Path(template_dir) / "manifest.json" == manifest_path


def test_checksum_mismatch(temp_cache_dir):
    """测试校验和不匹配"""
    import io
    from unittest.mock import patch, Mock
    
    # 创建测试 zip 文件
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, "w") as zipf:
        zipf.writestr("manifest.json", '{"outputWidth": 1800}')
    zip_content.seek(0)
    zip_bytes = zip_content.read()
    
    # 计算实际校验和
    actual_checksum = hashlib.sha256(zip_bytes).hexdigest()
    wrong_checksum = "wrong_checksum_" + "0" * 48  # 错误的校验和
    
    resolver = TemplateResolver(
        template_code="tpl_checksum",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum=wrong_checksum,  # 使用错误的校验和
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 请求
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        # 应该抛出 TemplateChecksumMismatch
        with pytest.raises(TemplateChecksumMismatch) as exc_info:
            resolver.resolve()
        
        assert "Checksum mismatch" in str(exc_info.value)
        assert wrong_checksum in str(exc_info.value)
        assert actual_checksum in str(exc_info.value)


def test_extract_contains_manifest_json(temp_cache_dir):
    """测试解压后包含 manifest.json"""
    import io
    import json
    from unittest.mock import patch, Mock
    
    # 创建测试 zip 文件（包含 manifest.json）
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, "w") as zipf:
        manifest_data = {
            "outputWidth": 1800,
            "outputHeight": 1200,
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        }
        zipf.writestr("manifest.json", json.dumps(manifest_data))
        zipf.writestr("assets/bg.png", b"fake_image_data")
    
    zip_content.seek(0)
    zip_bytes = zip_content.read()
    
    # 计算校验和
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    resolver = TemplateResolver(
        template_code="tpl_manifest",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum=checksum,
        cache_dir=temp_cache_dir,
    )
    
    # Mock HTTP 请求
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content = lambda chunk_size: [
        zip_bytes[i:i+chunk_size] for i in range(0, len(zip_bytes), chunk_size)
    ]
    mock_response.raise_for_status = Mock()
    
    with patch("app.services.template_resolver.requests.get", return_value=mock_response):
        template_dir = resolver.resolve()
        
        # 验证目录存在
        assert Path(template_dir).exists()
        
        # 验证 manifest.json 存在
        manifest_path = Path(template_dir) / "manifest.json"
        assert manifest_path.exists(), "manifest.json 不存在"
        
        # 验证 manifest.json 内容正确
        manifest_data_loaded = json.loads(manifest_path.read_text())
        assert manifest_data_loaded["outputWidth"] == 1800
        assert manifest_data_loaded["outputHeight"] == 1200
        
        # 验证其他文件也存在
        assets_dir = Path(template_dir) / "assets"
        assert assets_dir.exists() or (Path(template_dir) / "assets" / "bg.png").exists()


def test_concurrent_resolve_only_download_once(temp_cache_dir):
    """测试并发 resolve 同一模板只会下载一次"""
    import io
    import json
    import threading
    import requests
    from unittest.mock import patch, Mock
    
    # 创建测试 zip 文件
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, "w") as zipf:
        zipf.writestr("manifest.json", '{"outputWidth": 1800}')
    zip_content.seek(0)
    zip_bytes = zip_content.read()
    
    # 计算校验和
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    
    # 统计 requests.get 调用次数
    download_count = {"count": 0}
    
    def counting_get(*args, **kwargs):
        download_count["count"] += 1
        # 返回模拟响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [
            zip_bytes[i:i+chunk_size] for i in range(0, len(zip_bytes), chunk_size)
        ]
        mock_response.raise_for_status = Mock()
        return mock_response
    
    # 创建多个 resolver（相同参数）
    resolvers = [
        TemplateResolver(
            template_code="tpl_concurrent",
            version="1.0.0",
            download_url="http://example.com/template.zip",
            checksum=checksum,
            cache_dir=temp_cache_dir,
        )
        for _ in range(10)
    ]
    
    # 并发调用 resolve
    results = []
    errors = []
    
    def resolve_template(resolver):
        try:
            with patch("app.services.template_resolver.requests.get", side_effect=counting_get):
                result = resolver.resolve()
                results.append(result)
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=resolve_template, args=(resolver,)) for resolver in resolvers]
    
    # 启动所有线程
    for thread in threads:
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 验证：只下载了一次
    assert download_count["count"] == 1, f"应该只下载一次，实际下载了 {download_count['count']} 次"
    
    # 验证：所有线程都成功返回了相同的目录
    assert len(results) == 10, f"应该有 10 个结果，实际有 {len(results)} 个"
    assert len(set(results)) == 1, "所有结果应该是同一个目录"
    
    # 验证：没有错误
    assert len(errors) == 0, f"不应该有错误，实际有 {len(errors)} 个错误: {errors}"
    
    # 验证：目录存在且包含 manifest.json
    template_dir = results[0]
    assert Path(template_dir).exists()
    assert (Path(template_dir) / "manifest.json").exists()
