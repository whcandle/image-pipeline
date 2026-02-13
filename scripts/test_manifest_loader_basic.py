"""
测试 ManifestLoader 基础功能（load + validate）

验证：
1. 正常模板 load 成功
2. 手动改坏 JSON → 抛异常
3. 删字段能报错
"""

import sys
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.manifest_loader import (
    ManifestLoader,
    ManifestLoadError,
    ManifestValidationError,
)


def create_test_manifest(template_dir: Path, manifest_data: dict):
    """创建测试 manifest.json"""
    manifest_path = template_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return manifest_path


def test_load_success():
    """测试正常模板 load 成功"""
    print("=" * 60)
    print("测试 1: 正常模板 load 成功")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        
        # 创建有效的 manifest.json
        manifest_data = {
            "manifestVersion": 1,
            "templateCode": "tpl_001",
            "versionSemver": "0.1.1",
            "output": {
                "width": 1800,
                "height": 1200,
                "format": "png"
            },
            "assets": {
                "basePath": "assets"
            },
            "compose": {
                "background": "bg.png",
                "photos": [
                    {
                        "id": "p1",
                        "source": "raw",
                        "x": 100,
                        "y": 200,
                        "w": 800,
                        "h": 900
                    }
                ],
                "stickers": []
            }
        }
        
        create_test_manifest(template_dir, manifest_data)
        
        loader = ManifestLoader(str(template_dir))
        manifest = loader.load_manifest()
        
        print(f"[OK] load_manifest() 成功")
        print(f"   模板代码: {manifest.get('templateCode')}")
        print(f"   版本: {manifest.get('versionSemver')}")
        print(f"   输出尺寸: {manifest.get('output', {}).get('width')}x{manifest.get('output', {}).get('height')}")
        print(f"   照片数量: {len(manifest.get('compose', {}).get('photos', []))}")
        
        # 验证 validate_manifest
        try:
            loader.validate_manifest(manifest)
            print(f"[OK] validate_manifest() 通过")
        except ManifestValidationError as e:
            print(f"[FAIL] validate_manifest() 失败: {e}")
            return False
        
        return True


def test_invalid_json():
    """测试手动改坏 JSON → 抛异常"""
    print("\n" + "=" * 60)
    print("测试 2: 手动改坏 JSON → 抛异常")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        
        # 创建无效的 JSON
        manifest_path = template_dir / "manifest.json"
        manifest_path.write_text("{ invalid json }", encoding="utf-8")
        
        loader = ManifestLoader(str(template_dir))
        
        try:
            manifest = loader.load_manifest()
            print(f"[FAIL] 应该抛出 ManifestLoadError，但没有抛出")
            return False
        except ManifestLoadError as e:
            print(f"[OK] 正确抛出 ManifestLoadError: {e}")
            return True
        except Exception as e:
            print(f"[FAIL] 意外的异常类型: {type(e).__name__}: {e}")
            return False


def test_missing_manifest_file():
    """测试文件不存在 → 抛异常"""
    print("\n" + "=" * 60)
    print("测试 3: 文件不存在 → 抛异常")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        # 不创建 manifest.json
        
        loader = ManifestLoader(str(template_dir))
        
        try:
            manifest = loader.load_manifest()
            print(f"[FAIL] 应该抛出 ManifestLoadError，但没有抛出")
            return False
        except ManifestLoadError as e:
            print(f"[OK] 正确抛出 ManifestLoadError: {e}")
            return True
        except Exception as e:
            print(f"[FAIL] 意外的异常类型: {type(e).__name__}: {e}")
            return False


def test_missing_required_fields():
    """测试删字段能报错"""
    print("\n" + "=" * 60)
    print("测试 4: 删字段能报错")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "缺少 manifestVersion",
            "manifest": {
                "templateCode": "tpl_001",
                "versionSemver": "0.1.1",
                "output": {"width": 1800, "height": 1200},
                "compose": {"background": "bg.png", "photos": [{"id": "p1"}]}
            }
        },
        {
            "name": "缺少 templateCode",
            "manifest": {
                "manifestVersion": 1,
                "versionSemver": "0.1.1",
                "output": {"width": 1800, "height": 1200},
                "compose": {"background": "bg.png", "photos": [{"id": "p1"}]}
            }
        },
        {
            "name": "缺少 compose.photos",
            "manifest": {
                "manifestVersion": 1,
                "templateCode": "tpl_001",
                "versionSemver": "0.1.1",
                "output": {"width": 1800, "height": 1200},
                "compose": {"background": "bg.png"}
            }
        },
        {
            "name": "compose.photos 为空列表",
            "manifest": {
                "manifestVersion": 1,
                "templateCode": "tpl_001",
                "versionSemver": "0.1.1",
                "output": {"width": 1800, "height": 1200},
                "compose": {"background": "bg.png", "photos": []}
            }
        },
        {
            "name": "output.width 为负数",
            "manifest": {
                "manifestVersion": 1,
                "templateCode": "tpl_001",
                "versionSemver": "0.1.1",
                "output": {"width": -1, "height": 1200},
                "compose": {"background": "bg.png", "photos": [{"id": "p1"}]}
            }
        },
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        
        loader = ManifestLoader(str(template_dir))
        
        all_passed = True
        for test_case in test_cases:
            create_test_manifest(template_dir, test_case["manifest"])
            
            try:
                manifest = loader.load_manifest()
                loader.validate_manifest(manifest)
                print(f"[FAIL] {test_case['name']}: 应该抛出异常，但没有抛出")
                all_passed = False
            except ManifestValidationError as e:
                print(f"[OK] {test_case['name']}: 正确抛出 ManifestValidationError")
                print(f"   错误信息: {str(e)[:60]}...")
            except ManifestLoadError as e:
                print(f"[WARN] {test_case['name']}: 抛出 ManifestLoadError（可能是 JSON 格式问题）")
            except Exception as e:
                print(f"[FAIL] {test_case['name']}: 意外的异常类型: {type(e).__name__}: {e}")
                all_passed = False
        
        return all_passed


def test_print_manifest_keys():
    """测试打印 manifest key"""
    print("\n" + "=" * 60)
    print("测试 5: 打印 manifest key")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir) / "template"
        template_dir.mkdir()
        
        manifest_data = {
            "manifestVersion": 1,
            "templateCode": "tpl_001",
            "versionSemver": "0.1.1",
            "output": {
                "width": 1800,
                "height": 1200,
                "format": "png"
            },
            "assets": {
                "basePath": "assets"
            },
            "compose": {
                "background": "bg.png",
                "photos": [
                    {
                        "id": "p1",
                        "source": "raw",
                        "x": 100,
                        "y": 200,
                        "w": 800,
                        "h": 900
                    }
                ],
                "stickers": []
            }
        }
        
        create_test_manifest(template_dir, manifest_data)
        
        loader = ManifestLoader(str(template_dir))
        manifest = loader.load_manifest()
        
        print("Manifest 键:")
        print(f"  - manifestVersion: {manifest.get('manifestVersion')}")
        print(f"  - templateCode: {manifest.get('templateCode')}")
        print(f"  - versionSemver: {manifest.get('versionSemver')}")
        print(f"  - output: {list(manifest.get('output', {}).keys())}")
        print(f"  - assets: {list(manifest.get('assets', {}).keys())}")
        print(f"  - compose: {list(manifest.get('compose', {}).keys())}")
        print(f"  - compose.photos 数量: {len(manifest.get('compose', {}).get('photos', []))}")
        print(f"  - compose.stickers 数量: {len(manifest.get('compose', {}).get('stickers', []))}")
        
        return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("ManifestLoader 基础功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("正常模板 load 成功", test_load_success()))
    results.append(("手动改坏 JSON → 抛异常", test_invalid_json()))
    results.append(("文件不存在 → 抛异常", test_missing_manifest_file()))
    results.append(("删字段能报错", test_missing_required_fields()))
    results.append(("打印 manifest key", test_print_manifest_keys()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"  {status}: {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        print()
        print("说明：")
        print("- load_manifest() 可以正常读取和解析 JSON")
        print("- validate_manifest() 可以正确校验必填字段")
        print("- 缺少字段或字段类型错误时会抛出 ManifestValidationError")
        print("- JSON 格式错误或文件不存在时会抛出 ManifestLoadError")
        print()
        print("下一步：")
        print("1. 实现路径 normalize（相对路径 → 绝对路径）")
        print("2. 实现资源存在性校验")
        return 0
    else:
        print("=" * 60)
        print("[WARN] 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
