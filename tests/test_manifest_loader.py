"""
测试 ManifestLoader 模块（新版模板协议）

验证：
1. manifest.json 加载功能
2. manifest 结构验证功能
3. 错误处理（文件不存在、格式错误等）
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.manifest_loader import (
    ManifestLoader,
    ManifestLoadError,
    ManifestValidationError,
)


@pytest.fixture
def temp_template_dir():
    """创建临时模板目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _write_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _minimal_valid_manifest() -> dict:
    """构造一个满足当前 ManifestLoader 校验规则的最小 manifest"""
    return {
        "manifestVersion": 1,
        "templateCode": "tpl_001",
        "versionSemver": "0.1.0",
        "output": {
            "width": 1024,
            "height": 768,
            "format": "png",
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 0,
                    "y": 0,
                    "w": 100,
                    "h": 100,
                }
            ],
        },
    }


def test_manifest_loader_init(temp_template_dir):
    """测试 ManifestLoader 初始化"""
    loader = ManifestLoader(temp_template_dir)

    assert loader.template_dir == Path(temp_template_dir)
    assert loader.manifest_path == Path(temp_template_dir) / "manifest.json"


def test_load_manifest_success(temp_template_dir):
    """测试加载有效的 manifest.json"""
    manifest_data = _minimal_valid_manifest()
    manifest_path = Path(temp_template_dir) / "manifest.json"
    _write_manifest(manifest_path, manifest_data)

    loader = ManifestLoader(temp_template_dir)

    manifest = loader.load_manifest()
    # 再跑一次字段校验，确保不会抛异常
    loader.validate_manifest(manifest)

    assert manifest["templateCode"] == "tpl_001"
    assert manifest["output"]["width"] == 1024


def test_manifest_loader_not_found(temp_template_dir):
    """测试 manifest.json 不存在的情况"""
    loader = ManifestLoader(temp_template_dir)

    with pytest.raises(ManifestLoadError) as exc_info:
        loader.load_manifest()

    assert "manifest.json not found" in str(exc_info.value)


def test_manifest_loader_invalid_json(temp_template_dir):
    """测试无效的 JSON 格式"""
    manifest_path = Path(temp_template_dir) / "manifest.json"
    manifest_path.write_text("{ invalid json }", encoding="utf-8")

    loader = ManifestLoader(temp_template_dir)

    with pytest.raises(ManifestLoadError):
        loader.load_manifest()


def test_validate_manifest_missing_required_fields(temp_template_dir):
    """测试：缺少必填字段时应抛 ManifestValidationError（新版协议）"""
    # 故意缺少 compose.photos（必填）
    manifest_data = _minimal_valid_manifest()
    del manifest_data["compose"]["photos"]

    manifest_path = Path(temp_template_dir) / "manifest.json"
    _write_manifest(manifest_path, manifest_data)

    loader = ManifestLoader(temp_template_dir)
    manifest = loader.load_manifest()

    with pytest.raises(ManifestValidationError):
        loader.validate_manifest(manifest)
