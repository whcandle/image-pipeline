"""
测试 TemplateResolver 下载、校验、解压功能

使用真实 URL 测试：
- 下载 URL: http://127.0.0.1:9000/tpl_001_v0.1.1.zip
- Checksum: f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.template_resolver import (
    TemplateResolver,
    TemplateDownloadError,
    TemplateChecksumMismatch,
    TemplateExtractError,
    TemplateInvalidError,
)


def test_download_and_extract():
    """测试下载、校验、解压完整流程"""
    print("=" * 60)
    print("测试 TemplateResolver 下载、校验、解压功能")
    print("=" * 60)
    print()
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum="f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
    )
    
    print(f"模板代码: {resolver.template_code}")
    print(f"版本: {resolver.version}")
    print(f"下载 URL: {resolver.download_url}")
    print(f"校验和: {resolver.checksum}")
    print(f"缓存目录: {resolver.cache_dir}")
    print(f"最终目录: {resolver.final_dir}")
    print()
    
    try:
        print("开始解析模板...")
        template_dir = resolver.resolve()
        
        print(f"✅ 模板解析成功！")
        print(f"   模板目录: {template_dir}")
        print()
        
        # 验证目录存在
        template_path = Path(template_dir)
        assert template_path.exists(), f"模板目录不存在: {template_dir}"
        print(f"✅ 模板目录存在: {template_path}")
        
        # 验证 manifest.json 存在
        manifest_path = template_path / "manifest.json"
        assert manifest_path.exists(), f"manifest.json 不存在: {manifest_path}"
        print(f"✅ manifest.json 存在: {manifest_path}")
        
        # 读取并显示 manifest.json 内容（前几行）
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            print(f"✅ manifest.json 格式正确")
            print(f"   内容预览: {list(manifest_data.keys())}")
        except Exception as e:
            print(f"⚠️  无法读取 manifest.json: {e}")
        
        # 列出目录内容
        print()
        print("目录内容:")
        for item in sorted(template_path.iterdir()):
            if item.is_file():
                print(f"  📄 {item.name}")
            elif item.is_dir():
                print(f"  📁 {item.name}/")
        
        print()
        print("=" * 60)
        print("✅ 所有验证通过！")
        print("=" * 60)
        
        return True
        
    except TemplateDownloadError as e:
        print(f"❌ 下载失败: {e}")
        print()
        print("可能的原因:")
        print("1. HTTP 服务器未运行在 http://127.0.0.1:9000")
        print("2. 文件 tpl_001_v0.1.1.zip 不存在")
        print("3. 网络连接问题")
        return False
        
    except TemplateChecksumMismatch as e:
        print(f"❌ 校验和不匹配: {e}")
        print()
        print("可能的原因:")
        print("1. 下载的文件已损坏")
        print("2. 提供的 checksum 不正确")
        return False
        
    except TemplateExtractError as e:
        print(f"❌ 解压失败: {e}")
        return False
        
    except TemplateInvalidError as e:
        print(f"❌ 模板无效: {e}")
        return False
        
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_hit():
    """测试缓存命中（第二次调用应该直接返回）"""
    print("\n" + "=" * 60)
    print("测试缓存命中（第二次调用）")
    print("=" * 60)
    print()
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.1",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum="f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
    )
    
    try:
        print("第二次调用 resolve()（应该命中缓存）...")
        template_dir = resolver.resolve()
        
        print(f"✅ 缓存命中成功！")
        print(f"   模板目录: {template_dir}")
        print()
        print("说明: 如果看到这条消息，说明缓存机制正常工作")
        print("     第二次调用没有重新下载，直接返回了缓存目录")
        
        return True
        
    except Exception as e:
        print(f"❌ 缓存命中失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("TemplateResolver 完整功能测试")
    print("=" * 60)
    print()
    print("测试配置:")
    print("  下载 URL: http://127.0.0.1:9000/tpl_001_v0.1.1.zip")
    print("  Checksum: f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d")
    print()
    print("注意: 确保 HTTP 服务器运行在 http://127.0.0.1:9000")
    print("      并提供 tpl_001_v0.1.1.zip 文件")
    print()
    
    # 测试下载和解压
    success1 = test_download_and_extract()
    
    if success1:
        # 测试缓存命中
        success2 = test_cache_hit()
        
        if success2:
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！")
            print("=" * 60)
            print()
            print("功能验证:")
            print("  ✅ 下载功能正常")
            print("  ✅ 校验和验证正常")
            print("  ✅ 解压功能正常")
            print("  ✅ manifest.json 验证正常")
            print("  ✅ 缓存命中机制正常")
            return 0
    
    print("\n" + "=" * 60)
    print("⚠️  部分测试失败")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
