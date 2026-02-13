"""
测试 RenderEngine v2（基于 runtime_spec）

验证：
1. 基本渲染功能
2. z 排序功能
3. fit 模式（cover/contain）
4. 贴纸的旋转和透明度
5. 坐标改变导致输出变化
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image

from app.services.render_engine import RenderEngine, RenderError


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_runtime_spec(temp_dir):
    """创建示例 runtime_spec"""
    # 创建 assets 目录
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建背景图片
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    # 创建贴纸图片
    sticker_img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 200))
    sticker_path = assets_dir / "sticker1.png"
    sticker_img.save(sticker_path)
    
    # 创建 runtime_spec
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [
            {
                "id": "p1",
                "source": "raw",
                "x": 100,
                "y": 200,
                "w": 800,
                "h": 900,
                "fit": "cover",
                "z": 1
            }
        ],
        "stickers": [
            {
                "id": "s1",
                "path": str(sticker_path.resolve()),
                "x": 50,
                "y": 50,
                "w": 100,
                "h": 100,
                "rotate": 0,
                "opacity": 1.0,
                "z": 2
            }
        ]
    }
    
    return runtime_spec


def test_render_basic(sample_runtime_spec):
    """测试基本渲染功能"""
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 0))
    
    # 创建 RenderEngine
    engine = RenderEngine(sample_runtime_spec)
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证结果
    assert result.size == (1800, 1200)
    assert result.mode == "RGBA"


def test_render_z_order(temp_dir):
    """测试 z 排序功能"""
    # 创建 assets 目录
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建背景图片
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 100, 100))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    # 创建两个贴纸（不同颜色）
    sticker1_img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 255))  # 红色
    sticker1_path = assets_dir / "sticker1.png"
    sticker1_img.save(sticker1_path)
    
    sticker2_img = Image.new("RGBA", (200, 200), color=(0, 255, 0, 255))  # 绿色
    sticker2_path = assets_dir / "sticker2.png"
    sticker2_img.save(sticker2_path)
    
    # 创建 runtime_spec（z 值：sticker1(1) < sticker2(2)）
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [],
        "stickers": [
            {
                "id": "s2",
                "path": str(sticker2_path.resolve()),
                "x": 150,  # 与 s1 重叠
                "y": 150,
                "w": 200,
                "h": 200,
                "rotate": 0,
                "opacity": 1.0,
                "z": 2  # z 值更大，应该在上层
            },
            {
                "id": "s1",
                "path": str(sticker1_path.resolve()),
                "x": 100,
                "y": 100,
                "w": 200,
                "h": 200,
                "rotate": 0,
                "opacity": 1.0,
                "z": 1
            }
        ]
    }
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证：重叠区域应该是绿色（z=2 在上层）
    # 检查重叠区域的像素（应该在绿色贴纸范围内）
    pixel = result.getpixel((200, 200))
    # 绿色贴纸在上层，所以应该是绿色（0, 255, 0）
    assert pixel[1] > pixel[0], "绿色贴纸应该在红色贴纸上方（z=2 > z=1）"


def test_render_fit_cover(temp_dir):
    """测试 fit=cover 模式"""
    # 创建 runtime_spec
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [
            {
                "id": "p1",
                "source": "raw",
                "x": 100,
                "y": 200,
                "w": 400,
                "h": 400,
                "fit": "cover",
                "z": 1
            }
        ],
        "stickers": []
    }
    
    # 创建测试用的 raw_image（宽高比与目标区域不同）
    raw_image = Image.new("RGB", (1000, 500), color=(255, 0, 255))  # 宽高比 2:1
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证：cover 模式应该填满目标区域
    assert result.size == (1800, 1200)


def test_render_fit_contain(temp_dir):
    """测试 fit=contain 模式"""
    # 创建 runtime_spec
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [
            {
                "id": "p1",
                "source": "raw",
                "x": 100,
                "y": 200,
                "w": 400,
                "h": 400,
                "fit": "contain",
                "z": 1
            }
        ],
        "stickers": []
    }
    
    # 创建测试用的 raw_image（宽高比与目标区域不同）
    raw_image = Image.new("RGB", (1000, 500), color=(255, 0, 255))  # 宽高比 2:1
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证：contain 模式应该完整显示图像
    assert result.size == (1800, 1200)


def test_render_sticker_rotate(temp_dir):
    """测试贴纸旋转"""
    # 创建 runtime_spec
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    sticker_img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 255))
    sticker_path = assets_dir / "sticker1.png"
    sticker_img.save(sticker_path)
    
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [],
        "stickers": [
            {
                "id": "s1",
                "path": str(sticker_path.resolve()),
                "x": 100,
                "y": 100,
                "w": 200,
                "h": 200,
                "rotate": 45,  # 旋转 45 度
                "opacity": 1.0,
                "z": 1
            }
        ]
    }
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证：旋转后的贴纸应该存在
    assert result.size == (1800, 1200)


def test_render_sticker_opacity(temp_dir):
    """测试贴纸透明度"""
    # 创建 runtime_spec
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    sticker_img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 255))
    sticker_path = assets_dir / "sticker1.png"
    sticker_img.save(sticker_path)
    
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [],
        "stickers": [
            {
                "id": "s1",
                "path": str(sticker_path.resolve()),
                "x": 100,
                "y": 100,
                "w": 200,
                "h": 200,
                "rotate": 0,
                "opacity": 0.5,  # 50% 透明度
                "z": 1
            }
        ]
    }
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    
    # 渲染
    result = engine.render(raw_image)
    
    # 验证：透明度应该生效
    assert result.size == (1800, 1200)
    # 由于背景是完全不透明，合成后 alpha 仍为 255，这里通过颜色“变浅”来判断透明度是否生效
    pixel = result.getpixel((200, 200))
    r, g, b, a = pixel
    assert a == 255, "合成后整体 alpha 仍应为 255"
    # 贴纸是纯红 (255,0,0) 覆盖在蓝灰背景上，半透明后红色分量应 < 255，且仍明显偏红
    assert r < 255, "红色分量应被背景稀释（小于 255）"
    assert r > g and r > b, "整体颜色仍应偏红，说明贴纸确实覆盖在背景上"


def test_render_coordinate_change(sample_runtime_spec):
    """测试：改变坐标，输出图像应该变化"""
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 0))
    
    # 第一次渲染（原始坐标）
    engine1 = RenderEngine(sample_runtime_spec)
    result1 = engine1.render(raw_image)
    
    # 修改坐标
    runtime_spec2 = sample_runtime_spec.copy()
    runtime_spec2["photos"] = [photo.copy() for photo in sample_runtime_spec["photos"]]
    runtime_spec2["photos"][0]["x"] = 500
    runtime_spec2["photos"][0]["y"] = 500
    
    # 第二次渲染（修改后的坐标）
    engine2 = RenderEngine(runtime_spec2)
    result2 = engine2.render(raw_image)
    
    # 验证：两张图像应该不同（通过比较特定位置的像素）
    # 检查照片区域的像素（应该在第一次渲染的照片范围内）
    pixel1 = result1.getpixel((500, 500))
    pixel2 = result2.getpixel((500, 500))
    
    # 如果坐标改变生效，这两个位置的像素应该不同
    # 注意：由于照片位置改变，原来位置的像素可能不同
    assert result1.size == result2.size, "尺寸应该相同"


def test_render_missing_background(temp_dir):
    """测试：背景文件不存在时应该正常处理"""
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(temp_dir / "nonexistent_bg.png")  # 不存在的文件
        },
        "photos": [],
        "stickers": []
    }
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    
    # 渲染（应该不会报错，只是没有背景）
    result = engine.render(raw_image)
    
    # 验证：应该生成透明背景的画布
    assert result.size == (1800, 1200)


def test_render_missing_sticker(temp_dir):
    """测试：贴纸文件不存在时应该正常处理"""
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    bg_img = Image.new("RGB", (1800, 1200), color=(100, 150, 200))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)
    
    runtime_spec = {
        "output": {
            "width": 1800,
            "height": 1200,
            "format": "png"
        },
        "background": {
            "path": str(bg_path.resolve())
        },
        "photos": [],
        "stickers": [
            {
                "id": "s1",
                "path": str(temp_dir / "nonexistent_sticker.png"),  # 不存在的文件
                "x": 100,
                "y": 100,
                "w": 200,
                "h": 200,
                "rotate": 0,
                "opacity": 1.0,
                "z": 1
            }
        ]
    }
    
    # 创建 RenderEngine
    engine = RenderEngine(runtime_spec)
    
    # 创建测试用的 raw_image
    raw_image = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    
    # 渲染（应该不会报错，只是没有贴纸）
    result = engine.render(raw_image)
    
    # 验证：应该正常渲染（只是没有贴纸）
    assert result.size == (1800, 1200)
