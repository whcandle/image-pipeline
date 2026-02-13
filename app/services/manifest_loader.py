"""
Manifest Loader Module

This module is responsible for:
- Loading manifest.json from template directories
- Validating manifest.json structure and content
- Parsing manifest configuration

Single Responsibility: Manifest loading and validation.

重要原则：ManifestLoader 只负责"理解模板 + 把错误前置"，
不负责下载、不负责渲染。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class ManifestLoadError(Exception):
    """Manifest 加载失败（文件不存在或 JSON 解析错误）"""
    pass


class ManifestValidationError(Exception):
    """Manifest 验证失败（字段缺失、类型错误、数值非法）"""
    pass


class ManifestLoader:
    """
    Handles manifest.json loading and validation.
    
    Responsibilities:
    - Load manifest.json from template directory
    - Validate manifest structure and required fields
    - Parse and return manifest configuration
    
    重要原则：只负责"理解模板 + 把错误前置"，
    不负责下载、不负责渲染。
    """
    
    def __init__(self, template_dir: str):
        """
        Initialize the ManifestLoader.
        
        Args:
            template_dir: Path to the template directory containing manifest.json
        """
        self.template_dir = Path(template_dir)
        self.manifest_path = self.template_dir / "manifest.json"
    
    def load_manifest(self) -> Dict[str, Any]:
        """
        读取 template_dir/manifest.json 并解析 JSON。
        
        Returns:
            Parsed manifest configuration dictionary
            
        Raises:
            ManifestLoadError: 文件不存在或 JSON 解析错误
        """
        print(f"[ManifestLoader] Loading manifest from: {self.manifest_path}")
        print(f"[ManifestLoader] Template dir exists: {self.template_dir.exists()}")
        if self.template_dir.exists():
            print(f"[ManifestLoader] Template dir contents: {list(self.template_dir.iterdir())}")
        
        # 检查文件是否存在
        if not self.manifest_path.exists():
            print(f"[ManifestLoader] ❌ FAILED: manifest.json not found at {self.manifest_path}")
            raise ManifestLoadError(
                f"manifest.json not found at {self.manifest_path}"
            )
        
        # 读取并解析 JSON
        try:
            print(f"[ManifestLoader] Reading manifest.json...")
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"[ManifestLoader] ✅ Successfully loaded manifest.json")
            print(f"[ManifestLoader] Manifest keys: {list(manifest.keys())}")
        except json.JSONDecodeError as e:
            print(f"[ManifestLoader] ❌ FAILED: Failed to parse manifest.json: {e}")
            raise ManifestLoadError(f"Failed to parse manifest.json: {e}") from e
        except Exception as e:
            print(f"[ManifestLoader] ❌ FAILED: Error reading manifest.json: {e}")
            raise ManifestLoadError(f"Error reading manifest.json: {e}") from e
        
        return manifest
    
    def validate_manifest(self, manifest: Dict[str, Any]) -> None:
        """
        校验必填字段和字段类型。
        
        校验清单（A. 顶层必填）：
        - manifestVersion == 1
        - templateCode（非空字符串）
        - versionSemver（非空字符串）
        - output.width, output.height（正整数）
        - output.format（可选，默认 "png"）
        - assets.basePath（可选，默认 "assets"）
        - compose.background（必填，字符串）
        - compose.photos（必填，list，至少 1 个）
        - compose.stickers（可选，list，可为空）
        
        Args:
            manifest: Manifest dictionary to validate
            
        Raises:
            ManifestValidationError: If validation fails
        """
        print(f"[ManifestLoader] Starting manifest validation for template_dir={self.template_dir}")
        
        if not isinstance(manifest, dict):
            print(f"[ManifestLoader] ❌ FAILED: Manifest must be a dictionary, got {type(manifest)}")
            raise ManifestValidationError("Manifest must be a dictionary")
        
        # A.1: manifestVersion == 1
        print(f"[ManifestLoader] Checking manifestVersion...")
        if "manifestVersion" not in manifest:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: manifestVersion")
            raise ManifestValidationError("Missing required field: manifestVersion")
        if manifest["manifestVersion"] != 1:
            print(f"[ManifestLoader] ❌ FAILED: manifestVersion must be 1, got {manifest['manifestVersion']}")
            raise ManifestValidationError(
                f"manifestVersion must be 1, got {manifest['manifestVersion']}"
            )
        print(f"[ManifestLoader] ✅ manifestVersion = {manifest['manifestVersion']}")
        
        # A.2: templateCode（非空字符串）
        print(f"[ManifestLoader] Checking templateCode...")
        if "templateCode" not in manifest:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: templateCode")
            raise ManifestValidationError("Missing required field: templateCode")
        if not isinstance(manifest["templateCode"], str) or not manifest["templateCode"]:
            print(f"[ManifestLoader] ❌ FAILED: templateCode must be a non-empty string, got {manifest['templateCode']} (type: {type(manifest['templateCode'])})")
            raise ManifestValidationError(
                f"templateCode must be a non-empty string, got {manifest['templateCode']}"
            )
        print(f"[ManifestLoader] ✅ templateCode = {manifest['templateCode']}")
        
        # A.3: versionSemver（非空字符串）
        print(f"[ManifestLoader] Checking versionSemver...")
        if "versionSemver" not in manifest:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: versionSemver")
            raise ManifestValidationError("Missing required field: versionSemver")
        if not isinstance(manifest["versionSemver"], str) or not manifest["versionSemver"]:
            print(f"[ManifestLoader] ❌ FAILED: versionSemver must be a non-empty string, got {manifest['versionSemver']} (type: {type(manifest['versionSemver'])})")
            raise ManifestValidationError(
                f"versionSemver must be a non-empty string, got {manifest['versionSemver']}"
            )
        print(f"[ManifestLoader] ✅ versionSemver = {manifest['versionSemver']}")
        
        # A.4: output.width, output.height（正整数）
        print(f"[ManifestLoader] Checking output...")
        if "output" not in manifest:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: output")
            raise ManifestValidationError("Missing required field: output")
        if not isinstance(manifest["output"], dict):
            print(f"[ManifestLoader] ❌ FAILED: output must be a dictionary, got {type(manifest['output'])}")
            raise ManifestValidationError("output must be a dictionary")
        
        output = manifest["output"]
        print(f"[ManifestLoader] Checking output.width...")
        if "width" not in output:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: output.width")
            raise ManifestValidationError("Missing required field: output.width")
        if not isinstance(output["width"], int) or output["width"] <= 0:
            print(f"[ManifestLoader] ❌ FAILED: output.width must be a positive integer, got {output['width']} (type: {type(output['width'])})")
            raise ManifestValidationError(
                f"output.width must be a positive integer, got {output['width']}"
            )
        print(f"[ManifestLoader] ✅ output.width = {output['width']}")
        
        print(f"[ManifestLoader] Checking output.height...")
        if "height" not in output:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: output.height")
            raise ManifestValidationError("Missing required field: output.height")
        if not isinstance(output["height"], int) or output["height"] <= 0:
            print(f"[ManifestLoader] ❌ FAILED: output.height must be a positive integer, got {output['height']} (type: {type(output['height'])})")
            raise ManifestValidationError(
                f"output.height must be a positive integer, got {output['height']}"
            )
        print(f"[ManifestLoader] ✅ output.height = {output['height']}")
        
        # A.5: output.format（可选，默认 "png"）
        if "format" in output:
            print(f"[ManifestLoader] Checking output.format...")
            if not isinstance(output["format"], str):
                print(f"[ManifestLoader] ❌ FAILED: output.format must be a string, got {type(output['format'])}")
                raise ManifestValidationError("output.format must be a string")
            print(f"[ManifestLoader] ✅ output.format = {output['format']}")
        
        # A.6: assets.basePath（可选，默认 "assets"）
        if "assets" in manifest:
            print(f"[ManifestLoader] Checking assets...")
            if not isinstance(manifest["assets"], dict):
                print(f"[ManifestLoader] ❌ FAILED: assets must be a dictionary, got {type(manifest['assets'])}")
                raise ManifestValidationError("assets must be a dictionary")
            if "basePath" in manifest["assets"]:
                print(f"[ManifestLoader] Checking assets.basePath...")
                if not isinstance(manifest["assets"]["basePath"], str):
                    print(f"[ManifestLoader] ❌ FAILED: assets.basePath must be a string, got {type(manifest['assets']['basePath'])}")
                    raise ManifestValidationError("assets.basePath must be a string")
                print(f"[ManifestLoader] ✅ assets.basePath = {manifest['assets']['basePath']}")
        
        # A.7: compose.background（必填，字符串）
        print(f"[ManifestLoader] Checking compose...")
        if "compose" not in manifest:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: compose")
            raise ManifestValidationError("Missing required field: compose")
        if not isinstance(manifest["compose"], dict):
            print(f"[ManifestLoader] ❌ FAILED: compose must be a dictionary, got {type(manifest['compose'])}")
            raise ManifestValidationError("compose must be a dictionary")
        
        compose = manifest["compose"]
        print(f"[ManifestLoader] Checking compose.background...")
        if "background" not in compose:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: compose.background")
            raise ManifestValidationError("Missing required field: compose.background")
        if not isinstance(compose["background"], str):
            print(f"[ManifestLoader] ❌ FAILED: compose.background must be a string, got {compose['background']} (type: {type(compose['background'])})")
            raise ManifestValidationError(
                f"compose.background must be a string, got {compose['background']}"
            )
        print(f"[ManifestLoader] ✅ compose.background = {compose['background']}")
        
        # A.8: compose.photos（必填，list，至少 1 个）
        print(f"[ManifestLoader] Checking compose.photos...")
        if "photos" not in compose:
            print(f"[ManifestLoader] ❌ FAILED: Missing required field: compose.photos")
            raise ManifestValidationError("Missing required field: compose.photos")
        if not isinstance(compose["photos"], list):
            print(f"[ManifestLoader] ❌ FAILED: compose.photos must be a list, got {type(compose['photos'])}")
            raise ManifestValidationError("compose.photos must be a list")
        if len(compose["photos"]) < 1:
            print(f"[ManifestLoader] ❌ FAILED: compose.photos must contain at least 1 item, got {len(compose['photos'])}")
            raise ManifestValidationError("compose.photos must contain at least 1 item")
        print(f"[ManifestLoader] ✅ compose.photos has {len(compose['photos'])} item(s)")
        
        # A.9: compose.stickers（可选，list，可为空）
        if "stickers" in compose:
            print(f"[ManifestLoader] Checking compose.stickers...")
            if not isinstance(compose["stickers"], list):
                print(f"[ManifestLoader] ❌ FAILED: compose.stickers must be a list, got {type(compose['stickers'])}")
                raise ManifestValidationError("compose.stickers must be a list")
            print(f"[ManifestLoader] ✅ compose.stickers has {len(compose['stickers'])} item(s)")
        
        print(f"[ManifestLoader] ✅ Manifest structure validation passed!")
        
        # 暂时不做路径 normalize、不做文件存在性校验
        # 这些将在后续步骤中实现
    
    def to_runtime_spec(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 manifest 转换为 runtime spec（包含绝对路径）。
        
        功能：
        1. 读取 assets.basePath（默认 "assets"）
        2. 生成 background 的绝对路径
        3. 处理 stickers 的两种 src 规则
        4. 输出 runtime spec dict，包含所有必要字段，并为可选字段补默认值
        
        Args:
            manifest: 已验证的 manifest 字典
            
        Returns:
            Runtime spec 字典，包含：
            - templateCode, versionSemver
            - output (width/height/format)
            - backgroundAbsPath
            - photos[] (每个 photo 的 placement，补默认值 fit/z)
            - stickers[] (每个 sticker 的 abs path + placement，补默认值 rotate/opacity/z)
        """
        # 1. 读取 basePath（默认 "assets"）
        base_path = "assets"
        if "assets" in manifest and "basePath" in manifest["assets"]:
            base_path = manifest["assets"]["basePath"]
        
        # 2. 生成 background 的绝对路径
        compose = manifest["compose"]
        background_rel = compose["background"]
        background_abs = str(self.template_dir / base_path / background_rel)
        
        # 3. 处理 photos（补默认值）
        photos = []
        for photo in compose["photos"]:
            photo_spec = {
                "id": photo.get("id", ""),
                "source": photo.get("source", "raw"),
                "x": photo.get("x", 0),
                "y": photo.get("y", 0),
                "w": photo.get("w", 0),
                "h": photo.get("h", 0),
                "fit": photo.get("fit", "cover"),  # 默认 "cover"
                "z": photo.get("z", 0),  # 默认 0
            }
            photos.append(photo_spec)
        
        # 4. 处理 stickers（补默认值，并转换为绝对路径）
        stickers = []
        if "stickers" in compose:
            for sticker in compose["stickers"]:
                src = sticker.get("src", "")
                
                # 处理两种 src 规则
                if src.startswith("assets/") or src.startswith("assets\\"):
                    # 如果 src 以 "assets/" 开头，当作相对 template_dir
                    sticker_abs = str(self.template_dir / src)
                else:
                    # 否则，当作相对 basePath
                    sticker_abs = str(self.template_dir / base_path / src)
                
                sticker_spec = {
                    "id": sticker.get("id", ""),
                    "path": sticker_abs,  # 绝对路径
                    "x": sticker.get("x", 0),
                    "y": sticker.get("y", 0),
                    "w": sticker.get("w", 0),
                    "h": sticker.get("h", 0),
                    "rotate": sticker.get("rotate", 0),  # 默认 0
                    "opacity": sticker.get("opacity", 1.0),  # 默认 1.0
                    "z": sticker.get("z", 0),  # 默认 0
                }
                stickers.append(sticker_spec)
        
        # 5. 构建 runtime spec
        output = manifest["output"]
        runtime_spec = {
            "manifestVersion": manifest.get("manifestVersion", 1),
            "templateCode": manifest["templateCode"],
            "versionSemver": manifest["versionSemver"],
            "output": {
                "width": output["width"],
                "height": output["height"],
                "format": output.get("format", "png"),  # 默认 "png"
            },
            "background": {
                "path": background_abs,  # 绝对路径
            },
            "photos": photos,
            "stickers": stickers,
        }
        
        return runtime_spec
    
    def validate_assets(self, runtime_spec: Dict[str, Any]) -> None:
        """
        校验资源文件是否存在（早失败）。
        
        校验清单（B. 资源存在性）：
        - backgroundAbsPath 必须存在
        - 每个 stickerAbsPath 必须存在（stickers 非空）
        
        Args:
            runtime_spec: Runtime spec 字典（由 to_runtime_spec() 生成）
            
        Raises:
            ManifestValidationError: 如果资源文件不存在，错误信息包含路径
        """
        print(f"[ManifestLoader] Starting asset validation for template_dir={self.template_dir}")
        
        # 校验 background 文件存在
        background_path = Path(runtime_spec["background"]["path"])
        print(f"[ManifestLoader] Checking background file: {background_path}")
        if not background_path.exists():
            print(f"[ManifestLoader] ❌ FAILED: Background file not found: {background_path}")
            print(f"[ManifestLoader]   Template dir exists: {self.template_dir.exists()}")
            print(f"[ManifestLoader]   Template dir contents: {list(self.template_dir.iterdir()) if self.template_dir.exists() else 'N/A'}")
            raise ManifestValidationError(
                f"Background file not found: {background_path}"
            )
        print(f"[ManifestLoader] ✅ Background file exists: {background_path}")
        
        # 校验每个 sticker 文件存在
        stickers = runtime_spec.get("stickers", [])
        print(f"[ManifestLoader] Checking {len(stickers)} sticker file(s)...")
        for idx, sticker in enumerate(stickers):
            sticker_path = Path(sticker["path"])
            sticker_id = sticker.get('id', f'index_{idx}')
            print(f"[ManifestLoader] Checking sticker[{idx}] (id={sticker_id}): {sticker_path}")
            if not sticker_path.exists():
                print(f"[ManifestLoader] ❌ FAILED: Sticker file not found: {sticker_path} (sticker id: {sticker_id})")
                raise ManifestValidationError(
                    f"Sticker file not found: {sticker_path} (sticker id: {sticker_id})"
                )
            print(f"[ManifestLoader] ✅ Sticker file exists: {sticker_path}")
        
        print(f"[ManifestLoader] ✅ All asset files validation passed!")
    
    # 兼容方法：保持向后兼容
    def load(self) -> Dict[str, Any]:
        """
        兼容方法：加载并验证 manifest.json。
        
        内部调用 load_manifest() 和 validate_manifest()。
        
        Returns:
            Parsed manifest configuration dictionary
            
        Raises:
            ManifestLoadError: 文件不存在或 JSON 解析错误
            ManifestValidationError: 字段验证失败
        """
        manifest = self.load_manifest()
        self.validate_manifest(manifest)
        return manifest
    
    def validate(self, manifest: Dict[str, Any]) -> bool:
        """
        兼容方法：验证 manifest 结构。
        
        内部调用 validate_manifest()。
        
        Args:
            manifest: Manifest dictionary to validate
            
        Returns:
            True if manifest is valid
            
        Raises:
            ManifestValidationError: If validation fails
        """
        self.validate_manifest(manifest)
        return True
