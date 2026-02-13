"""
测试 RenderEngine 模块

验证：
1. 画布创建
2. 照片应用
3. 贴纸应用
4. 完整渲染流程
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image
from app.services.render_engine import RenderEngine, RenderError


@pytest.fixture
def sample_image():
    """创建示例图像"""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))  # 红色图像
    return img.convert("RGBA")


@pytest.fixture
def template_dir_with_sticker():
    """创建包含贴纸的模板目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template"
        template_path.mkdir()
        
        # 创建示例贴纸
        sticker = Image.new("RGBA", (50, 50), color=(0, 255, 0, 128))  # 半透明绿色
        sticker_path = template_path / "sticker.png"
        sticker.save(sticker_path)
        
        yield str(template_path)


def test_render_engine_init():
    """测试 RenderEngine 初始化"""
    manifest = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "backgroundColor": (255, 255, 255, 255),
    }
    
    engine = RenderEngine(manifest)
    assert engine.manifest == manifest
    assert engine.template_dir is None


def test_render_engine_create_canvas_from_size():
    """测试从尺寸创建画布"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "backgroundColor": (128, 128, 128, 255),
    }
    
    engine = RenderEngine(manifest)
    canvas = engine._create_canvas()
    
    assert canvas.size == (800, 600)
    assert canvas.mode == "RGBA"


def test_render_engine_create_canvas_from_background(template_dir_with_sticker):
    """测试从背景图创建画布"""
    # 创建背景图
    bg_path = Path(template_dir_with_sticker) / "background.png"
    bg_img = Image.new("RGB", (1000, 800), color=(200, 200, 200))
    bg_img.save(bg_path)
    
    manifest = {
        "background": "background.png",
    }
    
    engine = RenderEngine(manifest, template_dir=template_dir_with_sticker)
    canvas = engine._create_canvas()
    
    assert canvas.size == bg_img.size


def test_render_engine_apply_single_photo(sample_image):
    """测试应用单个照片（safeArea 方式）"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    engine = RenderEngine(manifest)
    canvas = engine._create_canvas()
    result = engine._apply_single_photo(canvas, sample_image)
    
    assert result.size == (800, 600)
    assert result.mode == "RGBA"


def test_render_engine_apply_photos(sample_image):
    """测试应用多个照片"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "photos": [
            {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
            {"x": 0.6, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FIT"},
        ],
    }
    
    engine = RenderEngine(manifest)
    canvas = engine._create_canvas()
    result = engine.apply_photos(canvas, manifest["photos"], sample_image)
    
    assert result.size == (800, 600)


def test_render_engine_apply_stickers(template_dir_with_sticker):
    """测试应用贴纸"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "stickers": [
            {"path": "sticker.png", "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1},
        ],
    }
    
    engine = RenderEngine(manifest, template_dir=template_dir_with_sticker)
    canvas = engine._create_canvas()
    result = engine.apply_stickers(canvas, manifest["stickers"])
    
    assert result.size == (800, 600)


def test_render_engine_full_render(sample_image):
    """测试完整渲染流程"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    engine = RenderEngine(manifest)
    result = engine.render(sample_image)
    
    assert result.size == (800, 600)
    assert result.mode == "RGBA"


def test_render_engine_render_with_photos(sample_image):
    """测试使用 photos 配置的渲染"""
    manifest = {
        "outputWidth": 800,
        "outputHeight": 600,
        "photos": [
            {"x": 0.2, "y": 0.2, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
        ],
    }
    
    engine = RenderEngine(manifest)
    result = engine.render(sample_image)
    
    assert result.size == (800, 600)
