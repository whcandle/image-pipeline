import sys
from pathlib import Path

from PIL import Image, ImageDraw

# 确保可以导入 app.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.render_engine import RenderEngine  # noqa: E402


def ensure_debug_background(debug_dir: Path, size=(1024, 768)) -> Path:
    """
    创建或返回一个简单的背景图，方便肉眼观察合成效果。
    """
    debug_dir.mkdir(parents=True, exist_ok=True)
    bg_path = debug_dir / "bg.png"
    if not bg_path.exists():
        bg_img = Image.new("RGB", size, color=(80, 130, 200))  # 蓝色背景
        bg_img.save(bg_path)
    return bg_path


def create_runtime_spec(bg_path: Path) -> dict:
    """
    构造一个最小可用的 runtime_spec：
    - 1 张背景
    - 1 个 photo 区域
    - 1 个 sticker（如果你后面想扩展）
    """
    width, height = 1024, 768

    runtime_spec = {
        "manifestVersion": 1,
        "templateCode": "tpl_smoke",
        "versionSemver": "0.1.0",
        "output": {
            "width": width,
            "height": height,
            "format": "png",
        },
        "background": {
            # RenderEngine 期望的是绝对路径
            "path": str(bg_path.resolve()),
        },
        "photos": [
            {
                "id": "p1",
                "source": "raw",
                "x": 200,
                "y": 180,
                "w": 300,
                "h": 300,
                "fit": "cover",
                "z": 1,
            }
        ],
        "stickers": [],
    }
    return runtime_spec


def create_raw_image(size=(1200, 1600)) -> Image.Image:
    """
    生成一张固定 raw 图：
    - 红色背景
    - 黑色对角线（方便观察裁剪/缩放和位置）
    """
    raw = Image.new("RGB", size, color=(220, 40, 40))
    draw = ImageDraw.Draw(raw)
    w, h = size
    draw.line((0, 0, w, h), fill=(0, 0, 0), width=10)
    draw.line((0, h, w, 0), fill=(0, 0, 0), width=10)
    return raw


def main() -> None:
    debug_dir = PROJECT_ROOT / "app" / "data" / "_debug"

    # 1. 准备背景和 runtime_spec
    bg_path = ensure_debug_background(debug_dir)
    runtime_spec = create_runtime_spec(bg_path)

    # 2. 生成 raw 图片
    raw_image = create_raw_image()

    # 3. 渲染
    engine = RenderEngine(runtime_spec)
    canvas = engine.render(raw_image)

    # 4. 保存输出
    output_path = debug_dir / "render_smoke.png"
    canvas.save(output_path)

    print(f"[OK] RenderEngine smoke test image saved to: {output_path.resolve()}")
    print("提示：修改 scripts/test_render_engine_smoke.py 中 runtime_spec.photos[0] 的 x/y/w/h，"
          "再次运行脚本，观察输出图片中照片区域是否对应变化。")


if __name__ == "__main__":
    main()

