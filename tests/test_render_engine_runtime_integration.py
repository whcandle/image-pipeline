"""
RenderEngine + ManifestLoader 集成测试（不依赖网络、不依赖真实模板包）

验证点：
1) 输出尺寸正确
2) 背景生效
3) 照片覆盖指定区域
4) 贴图按 z 覆盖照片
"""

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.services.manifest_loader import ManifestLoader
from app.services.render_engine import RenderEngine


def _create_template_and_runtime_spec(
    tmpdir: Path,
    *,
    with_sticker: bool = False,
    sticker_over_photo: bool = False,
) -> dict:
    """
    在临时目录下创建一个最小模板结构，并通过 ManifestLoader 生成 runtime_spec。

    目录结构：
    {tmpdir}/manifest.json
    {tmpdir}/assets/bg.png       纯绿色 1024x1024
    {tmpdir}/assets/sticker.png  纯蓝色 200x200（可选）
    """
    template_dir = tmpdir
    assets_dir = template_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 背景：纯绿色，方便断言
    bg_img = Image.new("RGB", (1024, 1024), color=(0, 255, 0))
    bg_path = assets_dir / "bg.png"
    bg_img.save(bg_path)

    manifest_compose = {
        "background": "bg.png",
        "photos": [
            {
                "id": "p1",
                "source": "raw",
                "x": 100,
                "y": 100,
                "w": 400,
                "h": 400,
                "fit": "cover",
                "z": 10,
            }
        ],
    }

    if with_sticker:
        # 贴图：纯蓝色
        sticker_img = Image.new("RGBA", (200, 200), color=(0, 0, 255, 255))
        sticker_path = assets_dir / "sticker.png"
        sticker_img.save(sticker_path)

        # 默认放在照片区域之上，且 z 更大
        if sticker_over_photo:
            sticker_x, sticker_y = 150, 150  # 与 photo 有重叠
        else:
            sticker_x, sticker_y = 600, 600  # 放在角落，不影响 photo 测试

        manifest_compose["stickers"] = [
            {
                "id": "s1",
                "src": "sticker.png",
                "x": sticker_x,
                "y": sticker_y,
                "w": 200,
                "h": 200,
                "rotate": 0,
                "opacity": 1.0,
                "z": 20,
            }
        ]
    else:
        manifest_compose["stickers"] = []

    manifest_data = {
        "manifestVersion": 1,
        "templateCode": "tpl_render_test",
        "versionSemver": "0.1.0",
        "output": {
            "width": 1024,
            "height": 1024,
            "format": "png",
        },
        "assets": {
            "basePath": "assets",
        },
        "compose": manifest_compose,
    }

    # 写入 manifest.json
    manifest_path = template_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # 通过 ManifestLoader 生成 runtime_spec
    loader = ManifestLoader(str(template_dir))
    manifest = loader.load_manifest()
    loader.validate_manifest(manifest)
    runtime_spec = loader.to_runtime_spec(manifest)
    loader.validate_assets(runtime_spec)

    return runtime_spec


def _color_close(rgb, expected, tol=10):
    return all(abs(int(c) - int(e)) <= tol for c, e in zip(rgb, expected))


def test_render_output_size_correct():
    """输出尺寸应与 manifest.output 一致"""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_spec = _create_template_and_runtime_spec(Path(tmpdir))

        # raw：纯红色
        raw_image = Image.new("RGB", (800, 1200), color=(255, 0, 0))

        engine = RenderEngine(runtime_spec)
        canvas = engine.render(raw_image)

        assert canvas.size == (1024, 1024)


def test_background_is_applied():
    """
    背景为纯绿色，且 (0,0) 不在 photo/sticker 区域，应该看到绿色。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_spec = _create_template_and_runtime_spec(Path(tmpdir), with_sticker=True)

        raw_image = Image.new("RGB", (800, 1200), color=(255, 0, 0))

        engine = RenderEngine(runtime_spec)
        canvas = engine.render(raw_image)

        pixel = canvas.getpixel((0, 0))  # 左上角不会被 photo/sticker 覆盖
        rgb = pixel[:3]
        assert _color_close(rgb, (0, 255, 0)), f"背景像素应接近绿色，实际为 {rgb}"


def test_photo_cover_changes_pixels():
    """
    photo 区域中心点应被 raw（纯红）覆盖，而不是绿色背景。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_spec = _create_template_and_runtime_spec(Path(tmpdir))

        # raw：纯红
        raw_image = Image.new("RGB", (800, 1200), color=(255, 0, 0))

        engine = RenderEngine(runtime_spec)
        canvas = engine.render(raw_image)

        # photo 区域：x=100,y=100,w=400,h=400 → 中心大约在 (300,300)
        pixel = canvas.getpixel((300, 300))
        rgb = pixel[:3]
        assert _color_close(rgb, (255, 0, 0)), f"photo 区域应接近红色，实际为 {rgb}"


def test_sticker_overlays_photo():
    """
    贴图为纯蓝色，z 比 photo 大，且与 photo 区域重叠。
    重叠区域应呈现蓝色（或接近蓝色）。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_spec = _create_template_and_runtime_spec(
            Path(tmpdir),
            with_sticker=True,
            sticker_over_photo=True,
        )

        raw_image = Image.new("RGB", (800, 1200), color=(255, 0, 0))

        engine = RenderEngine(runtime_spec)
        canvas = engine.render(raw_image)

        # 选一个同时在 photo 和 sticker 内的点，比如 (200,200)
        pixel = canvas.getpixel((200, 200))
        r, g, b, *_ = pixel
        # 预期蓝色分量最大
        assert b > r and b > g, f"重叠区域应被蓝色贴图覆盖，实际像素为 {(r, g, b)}"

