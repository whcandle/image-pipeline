"""
Segmentation Service Module

This module orchestrates the segmentation flow with fallback logic:
1. Try third-party provider (remove.bg, etc.)
2. Fallback to rembg if third-party fails
3. Fallback to raw if rembg fails (based on rules.segmentation.fallback)
"""

import time
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
import numpy as np

from app.services.segmentation.third_party_provider import (
    ThirdPartySegmentationProvider,
    SegmentationProviderError,
)
from app.clients.platform_client import PlatformClient, PlatformResolveError
from app.services.segment_service import SegmentService


class SegmentationService:
    """
    Orchestrates segmentation with fallback logic.
    
    Flow:
    1. Try third-party provider (remove.bg, etc.)
    2. Fallback to rembg if third-party fails
    3. Fallback to raw if rembg fails (based on rules.segmentation.fallback)
    """
    
    def __init__(self):
        """Initialize the service."""
        self.third_party_provider = ThirdPartySegmentationProvider()
        self.platform_client = PlatformClient()
        self.rembg_service = SegmentService()
    
    def segment(
        self,
        raw_image: Image.Image,
        template_code: str,
        version_semver: str,
        rules: Dict[str, Any],
    ) -> Tuple[Image.Image, List[Dict[str, Any]]]:
        """
        执行抠图，带降级逻辑。
        
        Args:
            raw_image: 原始图片（PIL Image）
            template_code: 模板代码
            version_semver: 模板版本号
            rules: 规则配置（从 RulesLoader 获取）
            
        Returns:
            (cutout_image, seg_notes)
            - cutout_image: 抠图结果（RGBA）或原始图片（如果降级到 raw）
            - seg_notes: 记录列表，包含：
                - seg.provider: removebg|rembg|raw
                - seg.fallback: rembg|raw（如果发生降级）
                - seg.reason: timeout|http_xxx|quality_low|exception
        """
        seg_notes = []
        
        # 提取 segmentation 规则
        seg_rules = self._extract_segmentation_rules(rules)
        
        # 1. 尝试 third-party provider
        cutout = None
        third_party_failed = False
        third_party_reason = None
        
        try:
            # 调用 platform resolve 获取 execution plan
            prefer = seg_rules.get("prefer", ["removebg", "rembg"])
            timeout_ms = seg_rules.get("timeoutMs", 6000)
            hint_params = {"output": "rgba"}
            if "hintParams" in seg_rules:
                hint_params.update(seg_rules["hintParams"])
            
            execution_plan = self.platform_client.resolve(
                template_code=template_code,
                version_semver=version_semver,
                prefer=prefer,
                timeout_ms=timeout_ms,
                hint_params=hint_params,
            )
            
            # 调用 third-party provider
            cutout = self.third_party_provider.process(raw_image, execution_plan)
            
            # 质量检查
            min_ratio = seg_rules.get("minSubjectAreaRatio", 0.08)
            subject_ratio = self._calculate_subject_area_ratio(cutout)
            
            if subject_ratio < min_ratio:
                # 质量不合格
                third_party_failed = True
                third_party_reason = f"quality_low (ratio={subject_ratio:.3f} < {min_ratio})"
                cutout = None
            else:
                # 成功
                provider_code = execution_plan.get("providerCode", "unknown")
                seg_notes.append({
                    "code": "seg.provider",
                    "message": f"Segmentation provider: {provider_code}",
                    "details": {
                        "provider": provider_code,
                        "subjectAreaRatio": subject_ratio,
                    }
                })
                return cutout, seg_notes
                
        except PlatformResolveError as e:
            third_party_failed = True
            third_party_reason = f"resolve_failed: {str(e)[:100]}"
        except SegmentationProviderError as e:
            third_party_failed = True
            if e.status_code:
                third_party_reason = f"http_{e.status_code}"
            else:
                third_party_reason = "exception"
        except Exception as e:
            third_party_failed = True
            third_party_reason = f"exception: {str(e)[:100]}"
        
        # 记录 third-party 失败
        if third_party_failed:
            seg_notes.append({
                "code": "SEG_THIRD_PARTY_FAIL",
                "message": f"Third-party segmentation failed: {third_party_reason}",
                "details": {
                    "reason": third_party_reason,
                }
            })
        
        # 2. 降级到 rembg
        if third_party_failed:
            try:
                # 使用 rembg（需要 RGBA 模式）
                feather_px = seg_rules.get("featherPx", 2)
                raw_rgba = raw_image.convert("RGBA") if raw_image.mode != "RGBA" else raw_image
                cutout, err_reason = self.rembg_service.segment_auto(raw_rgba, feather_px)
                
                if err_reason is None:
                    # rembg 成功
                    seg_notes.append({
                        "code": "seg.provider",
                        "message": f"Segmentation provider: rembg",
                        "details": {"provider": "rembg"}
                    })
                    seg_notes.append({
                        "code": "seg.fallback",
                        "message": "Fallback to rembg",
                        "details": {"fallback": "rembg", "reason": third_party_reason}
                    })
                    return cutout, seg_notes
                else:
                    # rembg 失败
                    raise Exception(f"rembg failed: {err_reason}")
                    
            except Exception as e:
                # rembg 也失败
                rembg_reason = str(e)[:100]
                seg_notes.append({
                    "code": "SEG_REMBG_FAIL",
                    "message": f"Rembg segmentation failed: {rembg_reason}",
                    "details": {"reason": rembg_reason}
                })
                
                # 3. 降级到 raw（根据 rules）
                fallback_mode = seg_rules.get("fallback", "raw")
                if fallback_mode == "raw":
                    seg_notes.append({
                        "code": "seg.provider",
                        "message": "Segmentation provider: raw",
                        "details": {"provider": "raw"}
                    })
                    seg_notes.append({
                        "code": "seg.fallback",
                        "message": "Fallback to raw",
                        "details": {
                            "fallback": "raw",
                            "reason": f"third_party: {third_party_reason}, rembg: {rembg_reason}"
                        }
                    })
                    return raw_image, seg_notes
                else:
                    # fallback 不是 raw，抛出异常
                    raise Exception(f"All segmentation methods failed, fallback={fallback_mode} is not 'raw'")
        
        # 理论上不会到这里
        return raw_image, seg_notes
    
    def _extract_segmentation_rules(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 rules 中提取 segmentation 配置。
        
        支持两种格式：
        1. 扁平化：{"segmentation.enabled": true, "segmentation.prefer": [...]}
        2. 嵌套：{"segmentation": {"enabled": true, "prefer": [...]}}
        """
        seg_rules = {}
        
        # 检查嵌套格式
        if "segmentation" in rules and isinstance(rules["segmentation"], dict):
            seg_rules = rules["segmentation"].copy()
        else:
            # 扁平化格式
            prefix = "segmentation."
            for key, value in rules.items():
                if key.startswith(prefix):
                    seg_key = key[len(prefix):]
                    seg_rules[seg_key] = value
        
        return seg_rules
    
    def _calculate_subject_area_ratio(self, image: Image.Image) -> float:
        """
        计算主体区域占比（基于 alpha 通道）。
        
        Args:
            image: RGBA 图片
            
        Returns:
            主体区域占比（0.0-1.0）
        """
        if image.mode != "RGBA":
            # 如果不是 RGBA，转换为 RGBA
            image = image.convert("RGBA")
        
        # 提取 alpha 通道
        alpha = np.array(image.split()[3])
        
        # 计算非透明像素数量
        non_transparent = np.sum(alpha > 0)
        
        # 计算总像素数
        total_pixels = alpha.size
        
        # 返回占比
        return non_transparent / total_pixels if total_pixels > 0 else 0.0
