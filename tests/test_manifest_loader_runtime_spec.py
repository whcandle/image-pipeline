"""
测试 ManifestLoader.to_runtime_spec() 方法

验证：
1. runtime spec 生成正确
2. 路径都正确（绝对路径）
3. 默认值补全
4. stickers 的两种 src 规则
"""

import pytest
import json
import tempfile
from pathlib import Path
from app.services.manifest_loader import ManifestLoader


@pytest.fixture
def temp_template_dir():
    """创建临时模板目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def create_test_template(template_dir: Path, manifest_data: dict):
    """创建测试模板目录结构"""
    template_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 manifest.json
    manifest_path = template_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    
    # 创建 assets 目录和文件
    base_path = manifest_data.get("assets", {}).get("basePath", "assets")
    assets_dir = template_dir / base_path
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建背景文件
    background = manifest_data["compose"]["background"]
    bg_path = assets_dir / background
    bg_path.touch()
    
    # 创建贴纸文件
    if "stickers" in manifest_data["compose"]:
        for sticker in manifest_data["compose"]["stickers"]:
            src = sticker.get("src", "")
            if src.startswith("assets/") or src.startswith("assets\\"):
                sticker_path = template_dir / src
            else:
                sticker_path = assets_dir / src
            sticker_path.parent.mkdir(parents=True, exist_ok=True)
            sticker_path.touch()
    
    return template_dir


def test_runtime_spec_basic(temp_template_dir):
    """测试基本的 runtime spec 生成"""
    template_dir = Path(temp_template_dir) / "template"
    
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
            "stickers": []
        }
    }
    
    create_test_template(template_dir, manifest_data)
    
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 验证基本字段
    assert runtime_spec["templateCode"] == "tpl_001"
    assert runtime_spec["versionSemver"] == "0.1.1"
    assert runtime_spec["output"]["width"] == 1800
    assert runtime_spec["output"]["height"] == 1200
    assert runtime_spec["output"]["format"] == "png"
    
    # 验证背景路径是绝对路径
    bg_path = Path(runtime_spec["background"]["path"])
    assert bg_path.is_absolute()
    assert bg_path.exists()
    
    # 验证路径正确
    expected_bg = template_dir / "assets" / "bg.png"
    assert bg_path.resolve() == expected_bg.resolve()
    
    # 验证 photos
    assert len(runtime_spec["photos"]) == 1
    assert runtime_spec["photos"][0]["id"] == "p1"
    assert runtime_spec["photos"][0]["source"] == "raw"
    
    # 验证 stickers
    assert len(runtime_spec["stickers"]) == 0


def test_runtime_spec_default_values(temp_template_dir):
    """测试默认值补全"""
    template_dir = Path(temp_template_dir) / "template"
    
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_002",
        "versionSemver": "1.0.0",
        "output": {
            "width": 1920,
            "height": 1080
            # 不提供 format，应该默认 "png"
        },
        "compose": {
            "background": "background.jpg",
            "photos": [
                {
                    "id": "p1",
                    "source": "raw",
                    "x": 100,
                    "y": 200,
                    "w": 800,
                    "h": 900
                    # 不提供 fit 和 z，应该使用默认值
                }
            ],
            "stickers": [
                {
                    "id": "s1",
                    "src": "sticker1.png",
                    "x": 50,
                    "y": 50,
                    "w": 100,
                    "h": 100
                    # 不提供 rotate, opacity, z，应该使用默认值
                }
            ]
        }
    }
    
    create_test_template(template_dir, manifest_data)
    
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 验证 output.format 默认值
    assert runtime_spec["output"]["format"] == "png"
    
    # 验证 photos fit 和 z 默认值
    photo = runtime_spec["photos"][0]
    assert photo["fit"] == "cover"
    assert photo["z"] == 0
    
    # 验证 stickers rotate, opacity, z 默认值
    sticker = runtime_spec["stickers"][0]
    assert sticker["rotate"] == 0
    assert sticker["opacity"] == 1.0
    assert sticker["z"] == 0


def test_stickers_src_rules(temp_template_dir):
    """测试 stickers 的两种 src 规则"""
    template_dir = Path(temp_template_dir) / "template"
    
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_003",
        "versionSemver": "1.0.0",
        "output": {
            "width": 1800,
            "height": 1200
        },
        "assets": {
            "basePath": "assets"
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {"id": "p1", "source": "raw", "x": 100, "y": 200, "w": 800, "h": 900}
            ],
            "stickers": [
                {
                    "id": "s1",
                    "src": "assets/sticker1.png",  # 以 assets/ 开头
                    "x": 50,
                    "y": 50,
                    "w": 100,
                    "h": 100
                },
                {
                    "id": "s2",
                    "src": "sticker2.png",  # 不以 assets/ 开头
                    "x": 150,
                    "y": 150,
                    "w": 100,
                    "h": 100
                }
            ]
        }
    }
    
    create_test_template(template_dir, manifest_data)
    
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 验证第一个 sticker（以 assets/ 开头）
    sticker1 = runtime_spec["stickers"][0]
    sticker1_path = Path(sticker1["path"])
    expected_path1 = template_dir / "assets" / "sticker1.png"
    assert sticker1_path.resolve() == expected_path1.resolve()
    
    # 验证第二个 sticker（不以 assets/ 开头）
    sticker2 = runtime_spec["stickers"][1]
    sticker2_path = Path(sticker2["path"])
    expected_path2 = template_dir / "assets" / "sticker2.png"
    assert sticker2_path.resolve() == expected_path2.resolve()


def test_runtime_spec_all_paths_absolute(temp_template_dir):
    """测试所有路径都是绝对路径"""
    template_dir = Path(temp_template_dir) / "template"
    
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_004",
        "versionSemver": "1.0.0",
        "output": {
            "width": 1800,
            "height": 1200
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {"id": "p1", "source": "raw", "x": 100, "y": 200, "w": 800, "h": 900}
            ],
            "stickers": [
                {"id": "s1", "src": "sticker1.png", "x": 50, "y": 50, "w": 100, "h": 100}
            ]
        }
    }
    
    create_test_template(template_dir, manifest_data)
    
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 验证背景路径是绝对路径
    bg_path = Path(runtime_spec["background"]["path"])
    assert bg_path.is_absolute()
    
    # 验证所有贴纸路径都是绝对路径
    for sticker in runtime_spec["stickers"]:
        sticker_path = Path(sticker["path"])
        assert sticker_path.is_absolute()


def test_runtime_spec_custom_base_path(temp_template_dir):
    """测试自定义 basePath"""
    template_dir = Path(temp_template_dir) / "template"
    
    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_005",
        "versionSemver": "1.0.0",
        "output": {
            "width": 1800,
            "height": 1200
        },
        "assets": {
            "basePath": "custom_assets"  # 自定义 basePath
        },
        "compose": {
            "background": "bg.png",
            "photos": [
                {"id": "p1", "source": "raw", "x": 100, "y": 200, "w": 800, "h": 900}
            ],
            "stickers": []
        }
    }
    
    create_test_template(template_dir, manifest_data)
    
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    
    # 验证背景路径使用自定义 basePath
    bg_path = Path(runtime_spec["background"]["path"])
    expected_bg = template_dir / "custom_assets" / "bg.png"
    assert bg_path.resolve() == expected_bg.resolve()
