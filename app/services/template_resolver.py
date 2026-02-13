"""
Template Resolver Module

This module is responsible for:
- Downloading templates from remote URLs
- Caching templates locally
- Validating template checksums
- Extracting template archives

Single Responsibility: Template download and cache management.

缓存策略：
- 缓存根目录：{TEMPLATE_CACHE_DIR} (默认: app/data/_templates)
- 最终模板目录：{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/
- 好处：checksum 变了自动新目录，不污染旧缓存；也支持同一版本多次发布
"""

import os
import hashlib
import zipfile
import shutil
import threading
from pathlib import Path
from typing import Optional
import requests
from app.config import settings


class TemplateDownloadError(Exception):
    """模板下载失败"""
    pass


class TemplateChecksumMismatch(Exception):
    """SHA256 校验和不匹配"""
    pass


class TemplateExtractError(Exception):
    """模板解压失败"""
    pass


class TemplateInvalidError(Exception):
    """模板无效（解压后缺 manifest.json）"""
    pass


class TemplateResolver:
    """
    Handles template downloading, caching, and extraction.
    
    缓存策略：
    - 缓存目录：{TEMPLATE_CACHE_DIR}/{templateCode}/{versionSemver}/{checksumSha256}/
    - 缓存命中：如果 final_dir/manifest.json 存在，直接返回目录
    - 缓存未命中：下载 zip → sha256 校验 → 解压到 tmp_dir → 原子切换 → 返回目录
    
    并发安全：
    - 使用进程内 dict + threading.Lock 保证同一模板只下载解压一次
    - lock key: {templateCode}:{versionSemver}:{checksumSha256}
    
    Responsibilities:
    - Download template archives from URLs
    - Verify checksums (SHA256)
    - Cache templates locally with checksum-based directory structure
    - Extract template archives atomically
    - Return template directory path
    """
    
    # 类级别的锁字典：{lock_key: threading.Lock}
    _locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()  # 保护 _locks 字典本身的锁
    
    def __init__(
        self,
        template_code: str,
        version: str,
        download_url: str,
        checksum: str,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the TemplateResolver.
        
        Args:
            template_code: Template identifier code (e.g., "tpl_001")
            version: Template version in semver format (e.g., "0.1.1")
            download_url: URL to download the template archive
            checksum: SHA256 checksum for validation (required)
            cache_dir: Base directory for template cache (default: settings.TEMPLATE_CACHE_DIR)
        """
        self.template_code = template_code
        self.version = version
        self.download_url = download_url
        self.checksum = checksum
        
        # 设置缓存根目录
        if cache_dir is None:
            # 使用配置的模板缓存目录，如果是相对路径则基于项目根目录
            cache_dir = settings.TEMPLATE_CACHE_DIR
            if not os.path.isabs(cache_dir):
                # 获取项目根目录（app 的父目录）
                project_root = Path(__file__).resolve().parent.parent.parent
                cache_dir = str(project_root / cache_dir)
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 最终模板目录：{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/
        self.final_dir = self._get_cache_dir()
    
    def _get_cache_dir(self) -> Path:
        """
        获取模板缓存目录路径。
        
        规则：{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/
        
        Returns:
            模板缓存目录路径
        """
        return self.cache_dir / self.template_code / self.version / self.checksum
    
    def _get_lock_key(self) -> str:
        """
        获取锁的 key。
        
        规则：{templateCode}:{versionSemver}:{checksumSha256}
        
        Returns:
            锁的 key
        """
        return f"{self.template_code}:{self.version}:{self.checksum}"
    
    def _get_lock(self) -> threading.Lock:
        """
        获取或创建锁。
        
        使用双重检查锁定模式确保线程安全。
        
        Returns:
            threading.Lock 对象
        """
        lock_key = self._get_lock_key()
        
        # 第一次检查（不加锁）
        if lock_key in self._locks:
            return self._locks[lock_key]
        
        # 加锁后再次检查
        with self._locks_lock:
            if lock_key not in self._locks:
                self._locks[lock_key] = threading.Lock()
            return self._locks[lock_key]
    
    def resolve(self) -> str:
        """
        解析模板：缓存命中直接返回，缓存未命中则下载、校验、解压。
        
        Returns:
            模板目录路径（绝对路径）
            
        Raises:
            TemplateDownloadError: 下载失败（非 200 / 超时）
            TemplateChecksumMismatch: SHA256 校验和不匹配
            TemplateExtractError: 解压失败
            TemplateInvalidError: 解压后缺 manifest.json
        """
        # Step 1: 检查缓存命中（不加锁，快速路径）
        manifest_path = self.final_dir / "manifest.json"
        if manifest_path.exists():
            # 缓存命中，直接返回
            return str(self.final_dir.resolve())
        
        # Step 2: 缓存未命中，需要下载和解压（加锁保护）
        lock = self._get_lock()
        
        with lock:
            # 双重检查：获取锁后再次检查缓存（可能其他线程已经下载完成）
            if manifest_path.exists():
                return str(self.final_dir.resolve())
            
            # 执行下载和解压
            zip_tmp_path = None
            extract_tmp_dir = None
            
            try:
                # 2.1 下载 zip 到临时文件
                zip_tmp_path = self._ensure_downloaded()
                
                # 2.2 计算 SHA256 并验证
                self._validate_checksum(zip_tmp_path)
                
                # 2.3 解压到临时目录
                extract_tmp_dir = Path(str(self.final_dir) + ".tmp")
                self._extract_zip(zip_tmp_path, extract_tmp_dir)
                
                # 2.4 原子切换到最终目录
                os.replace(extract_tmp_dir, self.final_dir)
                extract_tmp_dir = None  # 标记已成功切换，不需要清理
                
                # 2.5 返回最终目录
                return str(self.final_dir.resolve())
                
            finally:
                # 清理临时文件
                if zip_tmp_path and zip_tmp_path.exists():
                    try:
                        zip_tmp_path.unlink()
                    except Exception:
                        pass  # 忽略清理错误
                
                if extract_tmp_dir and extract_tmp_dir.exists():
                    try:
                        shutil.rmtree(extract_tmp_dir)
                    except Exception:
                        pass  # 忽略清理错误
    
    # TODO: 实现下载、校验、解压相关方法
    
    def _ensure_downloaded(self) -> Path:
        """
        确保模板已下载（如果未下载则下载）。
        
        下载流程：
        1. 下载 zip 文件到临时文件：{final_dir.parent}/{checksum}.zip.tmp
        2. 使用流式下载，避免内存问题
        
        Returns:
            下载的 zip 文件路径（临时文件）
            
        Raises:
            TemplateDownloadError: 下载失败（非 200 / 超时）
        """
        # 临时 zip 文件路径：{final_dir.parent}/{checksum}.zip.tmp
        zip_tmp_path = self.final_dir.parent / f"{self.checksum}.zip.tmp"
        
        try:
            # 确保父目录存在
            zip_tmp_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载文件（连接超时 5 秒，读取超时 30 秒）
            response = requests.get(
                self.download_url,
                stream=True,
                timeout=(5, 30)
            )
            response.raise_for_status()
            
            # 流式写入文件
            with open(zip_tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # 过滤掉 keep-alive 的空 chunk
                        f.write(chunk)
            
            return zip_tmp_path
            
        except requests.Timeout as e:
            # 清理部分下载的文件
            if zip_tmp_path.exists():
                zip_tmp_path.unlink()
            raise TemplateDownloadError(
                f"Download timeout for {self.download_url}: {e}"
            ) from e
        except requests.RequestException as e:
            # 清理部分下载的文件
            if zip_tmp_path.exists():
                zip_tmp_path.unlink()
            raise TemplateDownloadError(
                f"Failed to download template from {self.download_url}: {e}"
            ) from e
        except Exception as e:
            # 清理部分下载的文件
            if zip_tmp_path.exists():
                zip_tmp_path.unlink()
            raise TemplateDownloadError(
                f"Unexpected error during download: {e}"
            ) from e
    
    def _sha256_file(self, file_path: Path) -> str:
        """
        计算文件的 SHA256 校验和。
        
        Args:
            file_path: 文件路径
            
        Returns:
            SHA256 校验和（十六进制字符串，小写）
        """
        sha256_hash = hashlib.sha256()
        
        # 分块读取文件，避免大文件内存问题
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest().lower()
    
    def _validate_checksum(self, zip_path: Path) -> None:
        """
        验证 zip 文件的 SHA256 校验和。
        
        Args:
            zip_path: Zip 文件路径
            
        Raises:
            TemplateChecksumMismatch: 校验和不匹配
        """
        calculated_checksum = self._sha256_file(zip_path)
        expected_checksum = self.checksum.lower()
        
        if calculated_checksum != expected_checksum:
            raise TemplateChecksumMismatch(
                f"Checksum mismatch: expected {expected_checksum}, got {calculated_checksum}"
            )
    
    def _extract_zip(self, zip_path: Path, extract_tmp_dir: Path) -> None:
        """
        解压 zip 文件到临时目录。
        
        解压流程：
        1. 解压到临时目录：extract_tmp_dir
        2. 校验 {tmp_dir}/manifest.json 存在
        
        注意：原子切换（os.replace）在 resolve() 方法中完成
        
        Args:
            zip_path: Zip 文件路径
            extract_tmp_dir: 临时解压目录路径
            
        Raises:
            TemplateExtractError: 解压失败
            TemplateInvalidError: 解压后缺 manifest.json
        """
        try:
            # 确保临时目录的父目录存在
            extract_tmp_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果临时目录已存在，先清理
            if extract_tmp_dir.exists():
                shutil.rmtree(extract_tmp_dir)
            
            # 创建临时目录
            extract_tmp_dir.mkdir(parents=True, exist_ok=True)
            
            # 解压 zip 文件
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_tmp_dir)
            except zipfile.BadZipFile as e:
                raise TemplateExtractError(f"Invalid zip file: {zip_path}") from e
            except Exception as e:
                raise TemplateExtractError(f"Failed to extract zip file: {e}") from e
            
            # 校验 manifest.json 是否存在
            manifest_path = extract_tmp_dir / "manifest.json"
            if not manifest_path.exists():
                raise TemplateInvalidError(
                    f"manifest.json not found in extracted template at {extract_tmp_dir}"
                )
                
        except (TemplateExtractError, TemplateInvalidError):
            # 重新抛出这些异常
            raise
        except Exception as e:
            # 其他异常包装为 TemplateExtractError
            raise TemplateExtractError(f"Unexpected error during extraction: {e}") from e
