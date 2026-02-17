"""
Render Engine Module

This module is responsible for:
- Image composition and rendering
- Applying photos and stickers according to runtime_spec
- Handling z-order sorting
- Final image generation

Single Responsibility: Image composition and rendering.

重要原则：RenderEngine 只负责"把 runtime_spec 变成图像"，
不负责下载、不负责加载 manifest、不负责存储。
"""

import os
from pathlib import Path
from PIL import Image
from typing import Dict, Any, List, Optional
from app.utils.image_ops import fit_or_fill, open_image


class RenderError(Exception):
    """渲染错误"""
    pass


class RenderEngine:
    """
    Handles image composition and rendering based on runtime_spec.
    
    Responsibilities:
    - Create canvas from output dimensions
    - Render background image
    - Render photos (sorted by z-order)
    - Render stickers (sorted by z-order)
    - Generate final rendered image
    
    重要原则：只负责"把 runtime_spec 变成图像"。
    """
    
    def __init__(self, runtime_spec: Dict[str, Any]):
        """
        Initialize the RenderEngine.
        
        Args:
            runtime_spec: Runtime spec dictionary (from ManifestLoader.to_runtime_spec())
                Expected structure:
                {
                    "output": {"width": 1800, "height": 1200, "format": "png"},
                    "background": {"path": "绝对路径"},
                    "photos": [
                        {"id": "p1", "source": "raw", "x": 100, "y": 200, "w": 800, "h": 900, "fit": "cover", "z": 0}
                    ],
                    "stickers": [
                        {"id": "s1", "path": "绝对路径", "x": 50, "y": 50, "w": 100, "h": 100, "rotate": 0, "opacity": 1.0, "z": 0}
                    ]
                }
        """
        self.runtime_spec = runtime_spec
    
    def render(self, raw_image: Image.Image, artifacts: Optional[Dict[str, Image.Image]] = None) -> Image.Image:
        """
        根据 runtime_spec 渲染图像。
        
        流程：
        1. 创建画布（output.width/height）
        2. 画背景（background.path）
        3. 循环 photos[] 和 stickers[]（按 z 排序）
        4. 输出合成图像
        
        Args:
            raw_image: The input raw image (PIL Image)
            artifacts: 可选的艺术品字典，包含：
                - "cutout": 抠图结果（RGBA 图片），当 photo.source="cutout" 时使用
            
        Returns:
            Final rendered image (PIL Image, RGBA mode)
            
        Raises:
            RenderError: If rendering fails
        """
        try:
            # 1. 创建画布
            output = self.runtime_spec["output"]
            canvas = Image.new("RGBA", (output["width"], output["height"]), (0, 0, 0, 0))
            
            # 2. 渲染背景
            background_path = Path(self.runtime_spec["background"]["path"])
            if background_path.exists():
                background = open_image(str(background_path))
                # 调整背景尺寸以适应画布
                background = background.resize((output["width"], output["height"]), Image.LANCZOS)
                canvas.alpha_composite(background, (0, 0))
            
            # 3. 收集所有图层（photos + stickers）并按 z 排序
            layers = []
            
            # 添加 photos
            for photo in self.runtime_spec.get("photos", []):
                layers.append({
                    "type": "photo",
                    "data": photo,
                })
            
            # 添加 stickers
            for sticker in self.runtime_spec.get("stickers", []):
                layers.append({
                    "type": "sticker",
                    "data": sticker,
                })
            
            # 按 z 排序（低 z 值在前，先渲染）
            layers.sort(key=lambda x: x["data"].get("z", 0))
            
            # 4. 渲染每个图层
            for layer in layers:
                if layer["type"] == "photo":
                    self._render_photo(canvas, layer["data"], raw_image, artifacts)
                elif layer["type"] == "sticker":
                    self._render_sticker(canvas, layer["data"])
            
            return canvas
            
        except Exception as e:
            raise RenderError(f"Failed to render image: {e}") from e
    
    def _render_photo(self, canvas: Image.Image, photo: Dict[str, Any], raw_image: Image.Image, artifacts: Optional[Dict[str, Image.Image]] = None) -> None:
        """
        渲染照片到画布。
        
        Args:
            canvas: Canvas image (will be modified in place)
            photo: Photo configuration from runtime_spec
                {
                    "id": "p1",
                    "source": "raw" | "cutout",
                    "x": 100,  # 像素坐标
                    "y": 200,  # 像素坐标
                    "w": 800,  # 像素尺寸
                    "h": 900,  # 像素尺寸
                    "fit": "cover",  # "cover" 或 "contain"
                    "z": 0
                }
            raw_image: The input raw image (PIL Image)
            artifacts: 可选的艺术品字典，包含 cutout 图片
        """
        x = photo["x"]
        y = photo["y"]
        w = photo["w"]
        h = photo["h"]
        fit_mode = photo.get("fit", "cover")
        source = photo.get("source", "raw")
        
        # 选择图片源
        if source == "cutout" and artifacts and "cutout" in artifacts:
            # 使用抠图结果
            image_to_render = artifacts["cutout"]
        else:
            # 使用原始图片
            image_to_render = raw_image
        
        # 转换 fit 模式：cover -> FILL, contain -> FIT
        crop_mode = "FILL" if fit_mode == "cover" else "FIT"
        
        # 调整照片尺寸以适应目标区域
        placed = fit_or_fill(image_to_render.convert("RGBA"), w, h, crop_mode)
        
        # 合成到画布
        canvas.alpha_composite(placed, (x, y))
    
    def _render_sticker(self, canvas: Image.Image, sticker: Dict[str, Any]) -> None:
        """
        渲染贴纸到画布。
        
        Args:
            canvas: Canvas image (will be modified in place)
            sticker: Sticker configuration from runtime_spec
                {
                    "id": "s1",
                    "path": "绝对路径",
                    "x": 50,  # 像素坐标
                    "y": 50,  # 像素坐标
                    "w": 100,  # 像素尺寸
                    "h": 100,  # 像素尺寸
                    "rotate": 0,  # 旋转角度（度）
                    "opacity": 1.0,  # 透明度（0.0-1.0）
                    "z": 0
                }
        """
        sticker_path = Path(sticker["path"])
        if not sticker_path.exists():
            return
        
        # 加载贴纸
        sticker_img = open_image(str(sticker_path))
        
        # 调整尺寸
        w = sticker["w"]
        h = sticker["h"]
        if w > 0 and h > 0:
            sticker_img = sticker_img.resize((w, h), Image.LANCZOS)
        
        # 应用旋转
        rotate = sticker.get("rotate", 0)
        if rotate != 0:
            sticker_img = sticker_img.rotate(-rotate, expand=True)  # PIL rotate 是逆时针，所以取负
        
        # 应用透明度
        opacity = sticker.get("opacity", 1.0)
        if opacity < 1.0:
            # 调整 alpha 通道
            alpha = sticker_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            sticker_img.putalpha(alpha)
        
        # 合成到画布
        x = sticker["x"]
        y = sticker["y"]
        canvas.alpha_composite(sticker_img, (x, y))
