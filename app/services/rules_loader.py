"""
Rules Loader Module

This module is responsible for loading rules configuration from template directories.
Rules are loaded from manifest.assets.rules (default: "rules.json") with fallback to defaults.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


# 默认 rules（当 rules.json 不存在或解析失败时使用）
DEFAULT_RULES: Dict[str, Any] = {
    "segmentation.enabled": False,
    "segmentation.prefer": ["removebg", "rembg"],
    "segmentation.timeoutMs": 6000,
    "segmentation.fallback": "raw",
    "segmentation.minSubjectAreaRatio": 0.08,
    "segmentation.featherPx": 2,
    "segmentation.decontam": True,
}


@dataclass
class RulesLoadResult:
    """Rules 加载结果"""

    rules: Dict[str, Any]
    rules_loaded: bool
    rules_default_used: bool


class RulesLoader:
    """
    Handles loading of rules configuration for a given template directory.

    Responsibilities:
    - Load rules.json from template_dir/rules.json (template root directory)
    - Fallback to default rules if file missing or invalid
    - Return rules dict with load status flags
    """

    def __init__(self, template_dir: str) -> None:
        """
        Initialize the RulesLoader.

        Args:
            template_dir: Path to the template directory
        """
        self.template_dir = Path(template_dir)

    def _resolve_rules_path(self, base_path: str, rules_name: str) -> Path:
        """
        解析 rules 文件的完整路径。

        Args:
            base_path: assets 的 basePath（默认 "assets"），此参数保留用于兼容性，但不再使用
            rules_name: rules 文件名（默认 "rules.json"）

        Returns:
            rules 文件的完整路径（从模板根目录加载）
        """
        # rules.json 从模板根目录加载，不使用 base_path
        return self.template_dir / rules_name

    def load(self, manifest: Dict[str, Any]) -> RulesLoadResult:
        """
        加载 rules 配置。

        规则：
        1. 读取 manifest.assets.rules（默认 "rules.json"）
        2. 尝试从 template_dir/rules.json（模板根目录）读取 JSON
        3. 如果文件不存在/解析失败/不是 dict，返回默认 rules

        Args:
            manifest: 已验证的 manifest 字典

        Returns:
            RulesLoadResult 包含：
            - rules: 规则字典（默认或从文件加载）
            - rules_loaded: 是否成功从文件加载
            - rules_default_used: 是否使用了默认规则
        """
        # 读取 rules 文件名（从模板根目录加载，不使用 basePath）
        assets = manifest.get("assets") or {}
        rules_name = assets.get("rules", "rules.json")
        # base_path 保留用于兼容性，但不再用于路径计算
        base_path = assets.get("basePath", "assets")

        rules_path = self._resolve_rules_path(base_path, rules_name)

        try:
            # 检查文件是否存在
            if not rules_path.exists():
                return RulesLoadResult(
                    rules=dict(DEFAULT_RULES),
                    rules_loaded=False,
                    rules_default_used=True,
                )

            # 读取并解析 JSON
            with rules_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # 验证是 dict 类型
            if not isinstance(data, dict):
                return RulesLoadResult(
                    rules=dict(DEFAULT_RULES),
                    rules_loaded=False,
                    rules_default_used=True,
                )

            # 成功加载
            return RulesLoadResult(
                rules=data,
                rules_loaded=True,
                rules_default_used=False,
            )
        except Exception:
            # 任何异常都回退到默认规则（不抛出异常，保证流程不中断）
            return RulesLoadResult(
                rules=dict(DEFAULT_RULES),
                rules_loaded=False,
                rules_default_used=True,
            )
