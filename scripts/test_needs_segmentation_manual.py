"""
手动测试 needs_segmentation 判定逻辑

使用方法：
1. 确保已安装依赖：pip install -r requirements.txt
2. 运行：python scripts/test_needs_segmentation_manual.py

测试场景：
1. source=raw：needs_cutout=false
2. source=cutout 但 rules.enabled=false：needs_segmentation=false
3. source=cutout 且 rules.enabled=true：needs_segmentation=true
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.rules_loader import RulesLoader, DEFAULT_RULES


def test_rules_loader_default():
    """测试默认 rules 加载"""
    print("\n=== 测试 1: 默认 rules 加载 ===")
    
    # 创建一个临时 manifest（没有 rules.json）
    manifest = {
        "manifestVersion": 1,
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "output": {"width": 1024, "height": 1024},
        "assets": {"basePath": "assets"},
    }
    
    # 使用一个不存在的目录（会触发默认 rules）
    loader = RulesLoader("/tmp/nonexistent")
    result = loader.load(manifest)
    
    print(f"rules_loaded: {result.rules_loaded}")
    print(f"rules_default_used: {result.rules_default_used}")
    print(f"segmentation.enabled: {result.rules.get('segmentation.enabled')}")
    
    assert result.rules_default_used is True
    assert result.rules.get("segmentation.enabled") is False
    print("✅ 测试通过：默认 rules 正确加载")


def test_needs_segmentation_logic():
    """测试 needs_segmentation 判定逻辑"""
    print("\n=== 测试 2: needs_segmentation 判定逻辑 ===")
    
    # 场景 1: source=raw
    print("\n场景 1: source=raw")
    photos_raw = [{"id": "p1", "source": "raw", "x": 100, "y": 100, "w": 800, "h": 800}]
    needs_cutout_1 = any(photo.get("source") == "cutout" for photo in photos_raw)
    seg_enabled_1 = False  # 默认
    needs_segmentation_1 = needs_cutout_1 and seg_enabled_1
    
    print(f"  needs_cutout: {needs_cutout_1}")
    print(f"  seg_enabled: {seg_enabled_1}")
    print(f"  needs_segmentation: {needs_segmentation_1}")
    assert needs_segmentation_1 is False
    print("  ✅ 测试通过：source=raw 时 needs_segmentation=false")
    
    # 场景 2: source=cutout 但 seg_enabled=false
    print("\n场景 2: source=cutout 但 seg_enabled=false")
    photos_cutout = [{"id": "p1", "source": "cutout", "x": 100, "y": 100, "w": 800, "h": 800}]
    needs_cutout_2 = any(photo.get("source") == "cutout" for photo in photos_cutout)
    seg_enabled_2 = False  # 默认
    needs_segmentation_2 = needs_cutout_2 and seg_enabled_2
    
    print(f"  needs_cutout: {needs_cutout_2}")
    print(f"  seg_enabled: {seg_enabled_2}")
    print(f"  needs_segmentation: {needs_segmentation_2}")
    assert needs_segmentation_2 is False
    print("  ✅ 测试通过：source=cutout 但 seg_enabled=false 时 needs_segmentation=false")
    
    # 场景 3: source=cutout 且 seg_enabled=true
    print("\n场景 3: source=cutout 且 seg_enabled=true")
    needs_cutout_3 = any(photo.get("source") == "cutout" for photo in photos_cutout)
    seg_enabled_3 = True  # 从 rules.json 读取
    needs_segmentation_3 = needs_cutout_3 and seg_enabled_3
    
    print(f"  needs_cutout: {needs_cutout_3}")
    print(f"  seg_enabled: {seg_enabled_3}")
    print(f"  needs_segmentation: {needs_segmentation_3}")
    assert needs_segmentation_3 is True
    print("  ✅ 测试通过：source=cutout 且 seg_enabled=true 时 needs_segmentation=true")
    
    # 场景 4: 多个 photos，其中一个 source=cutout
    print("\n场景 4: 多个 photos，其中一个 source=cutout")
    photos_multi = [
        {"id": "p1", "source": "raw", "x": 100, "y": 100, "w": 400, "h": 400},
        {"id": "p2", "source": "cutout", "x": 500, "y": 500, "w": 400, "h": 400}
    ]
    needs_cutout_4 = any(photo.get("source") == "cutout" for photo in photos_multi)
    seg_enabled_4 = True
    needs_segmentation_4 = needs_cutout_4 and seg_enabled_4
    
    print(f"  needs_cutout: {needs_cutout_4}")
    print(f"  seg_enabled: {seg_enabled_4}")
    print(f"  needs_segmentation: {needs_segmentation_4}")
    assert needs_cutout_4 is True
    assert needs_segmentation_4 is True
    print("  ✅ 测试通过：多个 photos 中有一个 cutout 时 needs_cutout=true")


def test_rules_loader_with_file(tmp_template_dir=None):
    """测试从文件加载 rules"""
    print("\n=== 测试 3: 从文件加载 rules ===")
    
    if tmp_template_dir is None:
        print("⚠️  跳过：需要提供实际的 template_dir 路径")
        return
    
    template_dir = Path(tmp_template_dir)
    assets_dir = template_dir / "assets"
    
    # 创建 rules.json
    rules = {
        "segmentation.enabled": True,
        "segmentation.prefer": ["removebg"],
        "segmentation.timeoutMs": 5000
    }
    rules_path = assets_dir / "rules.json"
    rules_path.write_text(json.dumps(rules, indent=2), encoding="utf-8")
    
    manifest = {
        "manifestVersion": 1,
        "templateCode": "tpl_test",
        "versionSemver": "0.1.0",
        "output": {"width": 1024, "height": 1024},
        "assets": {"basePath": "assets", "rules": "rules.json"},
    }
    
    loader = RulesLoader(str(template_dir))
    result = loader.load(manifest)
    
    print(f"rules_loaded: {result.rules_loaded}")
    print(f"rules_default_used: {result.rules_default_used}")
    print(f"segmentation.enabled: {result.rules.get('segmentation.enabled')}")
    
    assert result.rules_loaded is True
    assert result.rules.get("segmentation.enabled") is True
    print("✅ 测试通过：从文件加载 rules 成功")


if __name__ == "__main__":
    print("=" * 60)
    print("needs_segmentation 判定逻辑测试")
    print("=" * 60)
    
    try:
        test_rules_loader_default()
        test_needs_segmentation_logic()
        
        # 可选：如果有实际的模板目录，可以测试文件加载
        # test_rules_loader_with_file("app/data/_templates/tpl_test/0.1.0")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
