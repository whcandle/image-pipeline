"""
Storage Manager Module

This module is responsible for:
- Storing rendered images to disk or cloud storage
- Generating URLs for stored images
- Managing storage paths and organization

Single Responsibility: Image storage and URL generation.
"""

import os
import uuid
from datetime import datetime
from PIL import Image
from pathlib import Path
from typing import Optional, Dict
from app.config import settings


class StorageError(Exception):
    """存储错误，消息中包含目标路径和原因"""

    def __init__(self, message: str, target_path: Optional[Path] = None):
        if target_path is not None:
            message = f"{message} (target: {target_path})"
        super().__init__(message)
        self.target_path = target_path


class StorageManager:
    """
    Handles image storage and URL generation.
    
    Responsibilities:
    - Store rendered images to specified location
    - Generate accessible URLs for stored images
    - Manage storage paths and file organization
    """
    
    def __init__(
        self,
        storage_base_path: Optional[str] = None,
        public_base_url: Optional[str] = None,
        subdirectory: str = "v2"
    ):
        """
        Initialize the StorageManager.
        
        Args:
            storage_base_path: Base directory path for storing images
            public_base_url: Base URL for generating public URLs (default: settings.PUBLIC_BASE_URL)
            subdirectory: Subdirectory name under storage_base_path (default: "v2")
        """
        if storage_base_path is None:
            # v2 本地存储默认直接使用 BOOTH_DATA_DIR 作为根目录
            # preview/final 会在此根目录下创建子目录：
            # {BOOTH_DATA_DIR}/preview/{jobId}/..., {BOOTH_DATA_DIR}/final/{jobId}/...
            storage_base_path = settings.BOOTH_DATA_DIR

        self.storage_base_path = Path(storage_base_path).resolve()
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        
        self.public_base_url = (public_base_url or settings.PUBLIC_BASE_URL).rstrip("/")
    
    # ------------------------
    # v1 通用存储接口（保留兼容性）
    # ------------------------
    def store(self, image: Image.Image, filename: Optional[str] = None) -> str:
        """
        Store the image and return the file path or URL.
        
        Args:
            image: PIL Image to store
            filename: Desired filename for the stored image (optional, auto-generated if not provided)
            
        Returns:
            URL to the stored image
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            # 生成文件名（如果未提供）
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{timestamp}_{unique_id}.jpg"
            
            # 确保文件名有扩展名
            if not filename.endswith(('.jpg', '.jpeg', '.png')):
                filename = f"{filename}.jpg"
            
            # 创建存储路径（按日期组织）
            date_str = datetime.now().strftime("%Y%m%d")
            date_dir = self.storage_base_path / date_str
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            file_path = date_dir / filename
            
            # 转换为 RGB（如果是 RGBA）
            if image.mode == "RGBA":
                rgb_image = image.convert("RGB")
            else:
                rgb_image = image.convert("RGB")
            
            # 保存为 JPEG
            rgb_image.save(file_path, format="JPEG", quality=90)
            
            # 返回 URL
            return self.get_url(str(file_path))
            
        except Exception as e:
            raise StorageError(
                f"Failed to store image: {e}",
                target_path=file_path if "file_path" in locals() else None,
            ) from e
    
    def get_url(self, file_path: str) -> str:
        """
        Generate a URL for the stored file.
        
        Args:
            file_path: Path to the stored file (absolute or relative to storage_base_path)
            
        Returns:
            Accessible URL for the file
        """
        file_path_obj = Path(file_path)
        
        # 如果是绝对路径，计算相对路径
        try:
            relative_path = file_path_obj.relative_to(self.storage_base_path)
        except ValueError:
            # 如果无法计算相对路径，使用文件名
            relative_path = file_path_obj.name
        
        # 转换为 URL 路径（使用正斜杠）
        url_path = str(relative_path).replace("\\", "/")
        
        # 生成完整 URL
        # 注意：这里假设文件通过 /files 静态文件服务提供
        # 需要根据实际的文件服务路径调整
        if url_path.startswith("v2/"):
            # 如果路径已经包含 v2，直接使用
            full_url = f"{self.public_base_url}/files/{url_path}"
        else:
            # 否则添加 v2 前缀
            full_url = f"{self.public_base_url}/files/v2/{url_path}"
        
        return full_url

    # ------------------------
    # v2 本地存储：preview / final
    # ------------------------
    def _ensure_image_mode(self, image: Image.Image, fmt: str) -> Image.Image:
        """确保图像在保存前处于可保存的模式（RGB/RGBA）。"""
        fmt_lower = fmt.lower()
        if fmt_lower in ("jpg", "jpeg"):
            # JPEG 不支持 alpha，统一转为 RGB
            return image.convert("RGB")
        # PNG 等支持 alpha，统一转为 RGBA，便于合成
        if image.mode not in ("RGB", "RGBA"):
            return image.convert("RGBA")
        return image

    def _store_kind(self, kind: str, job_id: str, image: Image.Image, fmt: str = "png") -> Dict[str, str]:
        """
        通用存储逻辑：保存 preview/final 图像，使用原子写入。

        目录结构：
            {storage_base_path}/{kind}/{jobId}/{name}.{fmt}

        kind: "preview" / "final"
        """
        name = "preview" if kind == "preview" else "final"
        fmt_lower = fmt.lower().lstrip(".")
        if fmt_lower == "jpeg":
            fmt_lower = "jpg"

        kind_dir = self.storage_base_path / kind / job_id
        kind_dir.mkdir(parents=True, exist_ok=True)

        final_path = (kind_dir / f"{name}.{fmt_lower}").resolve()
        tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")

        try:
            # 确保图像模式正确
            img_to_save = self._ensure_image_mode(image, fmt_lower)

            # 先写入临时文件
            img_to_save.save(tmp_path, format=fmt_upper_from_ext(fmt_lower))

            # 原子替换到最终文件
            os.replace(tmp_path, final_path)
        except Exception as e:
            # 清理临时文件
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise StorageError(
                f"Failed to store {kind} image: {e}",
                target_path=final_path,
            ) from e

        # 构造 URL：/files/{kind}/{jobId}/{name}.{fmt}
        url_path = f"/files/{kind}/{job_id}/{name}.{fmt_lower}"
        public_url = f"{self.public_base_url}{url_path}"

        return {
            "path": str(final_path),
            "url": public_url,
        }

    def store_preview(self, job_id: str, image: Image.Image, fmt: str = "png") -> Dict[str, str]:
        """存储预览图：{BOOTH_DATA_DIR}/preview/{jobId}/preview.{fmt}"""
        return self._store_kind("preview", job_id, image, fmt=fmt)

    def store_final(self, job_id: str, image: Image.Image, fmt: str = "png") -> Dict[str, str]:
        """存储最终图：{BOOTH_DATA_DIR}/final/{jobId}/final.{fmt}"""
        return self._store_kind("final", job_id, image, fmt=fmt)


def fmt_upper_from_ext(ext: str) -> str:
    """根据扩展名返回 Pillow 需要的 format 字符串。"""
    ext = ext.lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        return "JPEG"
    if ext == "png":
        return "PNG"
    # 回退
    return ext.upper() or "PNG"
