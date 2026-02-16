"""
StorageManager 冒烟测试：本地存储 preview/final 到 BOOTH_DATA_DIR。

运行方式（无需启动 FastAPI）：

    (py01) D:\workspace\image-pipeline> python scripts\test_storage_manager_smoke.py
"""

import sys
from pathlib import Path

from PIL import Image

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.services.storage_manager import StorageManager  # noqa: E402


def main() -> None:
    # 1. 创建一张简单图片
    img = Image.new("RGB", (400, 300), color=(200, 50, 50))

    # 2. 使用默认 BOOTH_DATA_DIR
    manager = StorageManager()

    job_id = "job_test_001"

    info = manager.store_final(job_id, img, fmt="png")

    path = Path(info["path"])
    url = info["url"]

    print(f"[OK] final stored path: {path}")
    print(f"[OK] final public url: {url}")

    assert path.exists(), f"file should exist: {path}"

    print("[OK] StorageManager smoke test passed.")


if __name__ == "__main__":
    main()

