# tests/conftest.py
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# =========================================================
# 确保 pytest 运行时能找到项目根目录（image-pipeline）
# =========================================================
# 当前文件：.../image-pipeline/tests/conftest.py
# parent.parent 即项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 把项目根目录加入 Python 模块搜索路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 现在再导入 app.main 就一定能找到
from app.main import app


@pytest.fixture()
def client():
    """
    FastAPI TestClient fixture
    """
    return TestClient(app)
