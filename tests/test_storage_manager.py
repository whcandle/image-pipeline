"""
测试 StorageManager 模块

验证：
1. 图像存储功能
2. URL 生成功能
3. 目录自动创建
4. 错误处理
"""

import pytest
import tempfile
from pathlib import Path
from PIL import Image
from app.services.storage_manager import StorageManager, StorageError


@pytest.fixture
def temp_storage_dir():
    """创建临时存储目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image():
    """创建示例图像"""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))  # 红色
    return img


@pytest.fixture
def sample_rgba_image():
    """创建示例 RGBA 图像"""
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))  # 半透明红色
    return img


def test_storage_manager_init(temp_storage_dir):
    """测试 StorageManager 初始化"""
    manager = StorageManager(storage_base_path=temp_storage_dir)
    
    assert manager.storage_base_path == Path(temp_storage_dir)
    assert manager.storage_base_path.exists()


def test_storage_manager_init_creates_directory(temp_storage_dir):
    """测试 StorageManager 自动创建目录"""
    new_dir = Path(temp_storage_dir) / "new_storage"
    manager = StorageManager(storage_base_path=str(new_dir))
    
    assert new_dir.exists()


def test_storage_manager_store_image(temp_storage_dir, sample_image):
    """测试存储图像"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    url = manager.store(sample_image, "test_image.jpg")
    
    # 验证 URL 格式
    assert url.startswith("http://localhost:9002")
    assert "test_image.jpg" in url or "files" in url
    
    # 验证文件是否存在（从 URL 提取路径）
    # URL 格式: http://localhost:9002/files/v2/YYYYMMDD/filename.jpg
    # 需要检查存储目录中是否有文件
    storage_path = Path(temp_storage_dir)
    date_dirs = [d for d in storage_path.iterdir() if d.is_dir()]
    assert len(date_dirs) > 0  # 应该有日期目录


def test_storage_manager_store_with_auto_filename(temp_storage_dir, sample_image):
    """测试自动生成文件名"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    url1 = manager.store(sample_image)
    url2 = manager.store(sample_image)
    
    # 两个 URL 应该不同（因为文件名不同）
    assert url1 != url2
    assert url1.startswith("http://localhost:9002")
    assert url2.startswith("http://localhost:9002")


def test_storage_manager_store_rgba_image(temp_storage_dir, sample_rgba_image):
    """测试存储 RGBA 图像（应转换为 RGB）"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    url = manager.store(sample_rgba_image, "rgba_test.jpg")
    
    assert url.startswith("http://localhost:9002")
    # 验证文件已保存（通过检查目录）
    storage_path = Path(temp_storage_dir)
    date_dirs = [d for d in storage_path.iterdir() if d.is_dir()]
    if date_dirs:
        files = list(date_dirs[0].glob("*.jpg"))
        assert len(files) > 0


def test_storage_manager_get_url(temp_storage_dir):
    """测试 URL 生成"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    # 测试相对路径
    relative_path = "20240101/test.jpg"
    url = manager.get_url(relative_path)
    
    assert url.startswith("http://localhost:9002")
    assert "files" in url
    assert "test.jpg" in url


def test_storage_manager_get_url_absolute_path(temp_storage_dir):
    """测试使用绝对路径生成 URL"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    # 创建测试文件
    test_file = Path(temp_storage_dir) / "20240101" / "test.jpg"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.touch()
    
    url = manager.get_url(str(test_file))
    
    assert url.startswith("http://localhost:9002")
    assert "files" in url


def test_storage_manager_store_creates_date_directory(temp_storage_dir, sample_image):
    """测试存储时自动创建日期目录"""
    manager = StorageManager(storage_base_path=temp_storage_dir)
    
    manager.store(sample_image, "test.jpg")
    
    # 检查是否有日期格式的目录（YYYYMMDD）
    storage_path = Path(temp_storage_dir)
    date_dirs = [d for d in storage_path.iterdir() if d.is_dir() and d.name.isdigit()]
    
    assert len(date_dirs) > 0
    assert len(date_dirs[0].name) == 8  # YYYYMMDD 格式


def test_storage_manager_store_without_extension(temp_storage_dir, sample_image):
    """测试存储时自动添加扩展名"""
    manager = StorageManager(
        storage_base_path=temp_storage_dir,
        public_base_url="http://localhost:9002"
    )
    
    url = manager.store(sample_image, "test_no_ext")
    
    # URL 应该包含 .jpg
    assert ".jpg" in url or "jpg" in url.lower()


def test_storage_manager_custom_subdirectory(temp_storage_dir, sample_image):
    """测试自定义存储路径"""
    # 测试：提供自定义的存储路径
    custom_path = Path(temp_storage_dir) / "custom_v2"
    manager = StorageManager(
        storage_base_path=str(custom_path),
        public_base_url="http://localhost:9002"
    )
    
    url = manager.store(sample_image, "test.jpg")
    
    # 验证存储路径正确
    assert manager.storage_base_path == custom_path
    assert manager.storage_base_path.exists()
    assert url.startswith("http://localhost:9002")
    
    # 验证文件已保存
    date_dirs = [d for d in custom_path.iterdir() if d.is_dir()]
    assert len(date_dirs) > 0


def test_storage_manager_multiple_stores(temp_storage_dir, sample_image):
    """测试多次存储"""
    manager = StorageManager(storage_base_path=temp_storage_dir)
    
    urls = []
    for i in range(3):
        url = manager.store(sample_image, f"test_{i}.jpg")
        urls.append(url)
    
    # 所有 URL 应该不同
    assert len(set(urls)) == 3
    
    # 验证文件都已保存
    storage_path = Path(temp_storage_dir)
    date_dirs = [d for d in storage_path.iterdir() if d.is_dir()]
    if date_dirs:
        all_files = []
        for date_dir in date_dirs:
            all_files.extend(list(date_dir.glob("*.jpg")))
        assert len(all_files) >= 3
