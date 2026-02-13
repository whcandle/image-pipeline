"""
最简单的测试方法：验证 TemplateResolver 并发锁功能

使用方法：
    python scripts/simple_test_template_resolver.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("TemplateResolver 并发锁功能验证")
print("=" * 60)
print()

try:
    from app.services.template_resolver import TemplateResolver
    
    print("✅ 导入成功")
    print()
    
    # 测试 1: 验证锁机制存在
    print("测试 1: 验证锁机制")
    print("-" * 60)
    
    resolver1 = TemplateResolver(
        template_code="tpl_test",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum="test_checksum",
    )
    
    # 验证锁方法存在
    assert hasattr(resolver1, "_get_lock"), "缺少 _get_lock 方法"
    assert hasattr(resolver1, "_get_lock_key"), "缺少 _get_lock_key 方法"
    assert hasattr(TemplateResolver, "_locks"), "缺少类级别的 _locks 字典"
    
    # 验证锁 key 格式
    lock_key = resolver1._get_lock_key()
    assert lock_key == "tpl_test:1.0.0:test_checksum", f"锁 key 格式错误: {lock_key}"
    
    print(f"✅ 锁机制存在")
    print(f"   锁 key: {lock_key}")
    print()
    
    # 测试 2: 验证锁字典
    print("测试 2: 验证锁字典")
    print("-" * 60)
    
    resolver2 = TemplateResolver(
        template_code="tpl_test",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum="test_checksum",
    )
    
    # 应该使用同一个锁
    lock1 = resolver1._get_lock()
    lock2 = resolver2._get_lock()
    assert lock1 is lock2, "相同模板应该使用同一个锁"
    
    print(f"✅ 相同模板使用同一个锁")
    print(f"   锁对象: {lock1}")
    print()
    
    # 测试 3: 验证不同模板使用不同锁
    print("测试 3: 验证不同模板使用不同锁")
    print("-" * 60)
    
    resolver3 = TemplateResolver(
        template_code="tpl_other",
        version="1.0.0",
        download_url="http://example.com/template.zip",
        checksum="test_checksum",
    )
    
    lock3 = resolver3._get_lock()
    assert lock3 is not lock1, "不同模板应该使用不同的锁"
    
    print(f"✅ 不同模板使用不同的锁")
    print(f"   模板1 锁: {lock1}")
    print(f"   模板3 锁: {lock3}")
    print()
    
    print("=" * 60)
    print("✅ 所有基本验证通过！")
    print("=" * 60)
    print()
    print("说明：")
    print("- 并发锁机制已实现")
    print("- 锁的 key 格式正确：{templateCode}:{version}:{checksum}")
    print("- 相同模板使用同一个锁")
    print("- 不同模板使用不同的锁")
    print()
    print("完整测试（需要 pytest 和依赖）:")
    print("  pytest tests/test_template_resolver.py -q")
    print()
    print("新增的 4 个测试用例：")
    print("  1. test_cache_hit - 缓存命中测试")
    print("  2. test_checksum_mismatch - 校验和不匹配测试")
    print("  3. test_extract_contains_manifest_json - 解压包含 manifest.json 测试")
    print("  4. test_concurrent_resolve_only_download_once - 并发只下载一次测试")
    
    sys.exit(0)
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("   请确保在正确的环境中运行（已安装依赖）")
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
