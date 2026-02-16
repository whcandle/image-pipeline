"""
测试模板下载功能（仅下载，不进行完整处理）

使用方法：
    python scripts/test_template_download_only.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("模板下载功能测试（仅测试下载和解压）")
print("=" * 60)
print()

try:
    from app.services.template_resolver import (
        TemplateResolver,
        TemplateDownloadError,
        TemplateChecksumMismatch,
        TemplateExtractError,
        TemplateInvalidError
    )
    
    print("✅ 导入成功")
    print()
    
    # 从命令行参数或使用默认值
    if len(sys.argv) >= 6:
        template_code = sys.argv[1]
        version_semver = sys.argv[2]
        download_url = sys.argv[3]
        checksum_sha256 = sys.argv[4]
        raw_path = sys.argv[5] if len(sys.argv) > 5 else None
    else:
        # 使用默认值（从用户的 curl 命令中提取）
        template_code = "tpl_002"
        version_semver = "0.1.2"
        download_url = "http://127.0.0.1:9000/tpl_002_v0.1.2.zip"
        checksum_sha256 = "307ac5fa4c429d2bf9e1d5afba29681a13c0047e51cc2fd21ca746eae4f87420"
        raw_path = "D:/AICreama/imagePipeLineTmp/test.jpg"
        print("使用默认参数（从您的 curl 命令中提取）")
        print("如需自定义，请使用：")
        print("  python scripts/test_template_download_only.py <templateCode> <versionSemver> <downloadUrl> <checksumSha256> [rawPath]")
        print()
    
    print("测试参数：")
    print(f"  Template Code: {template_code}")
    print(f"  Version: {version_semver}")
    print(f"  Download URL: {download_url}")
    print(f"  Checksum: {checksum_sha256}")
    print()
    
    # 创建 TemplateResolver
    print("创建 TemplateResolver...")
    resolver = TemplateResolver(
        template_code=template_code,
        version=version_semver,
        download_url=download_url,
        checksum=checksum_sha256
    )
    
    print(f"✅ TemplateResolver 创建成功")
    print(f"   缓存目录: {resolver.cache_dir}")
    print(f"   最终目录: {resolver.final_dir}")
    print()
    
    # 执行下载和解析
    print("开始下载和解析模板...")
    print("-" * 60)
    
    try:
        template_dir = resolver.resolve()
        print()
        print("✅ 模板下载和解析成功！")
        print(f"   模板目录: {template_dir}")
        print()
        
        # 检查 manifest.json 是否存在
        manifest_path = Path(template_dir) / "manifest.json"
        if manifest_path.exists():
            print("✅ manifest.json 存在")
            print(f"   路径: {manifest_path}")
        else:
            print("⚠️  manifest.json 不存在（这不应该发生）")
        
        # 列出模板目录内容
        print()
        print("模板目录内容：")
        template_path = Path(template_dir)
        if template_path.exists():
            for item in sorted(template_path.iterdir()):
                if item.is_file():
                    print(f"  📄 {item.name} ({item.stat().st_size} bytes)")
                elif item.is_dir():
                    print(f"  📁 {item.name}/")
        
        print()
        print("=" * 60)
        print("✅ 测试完成！模板已成功下载到 pipeline")
        print("=" * 60)
        print()
        print("说明：")
        print("- 模板已下载并解压到缓存目录")
        print("- 如果再次运行相同命令，会使用缓存（不会重新下载）")
        print("- 要测试完整处理流程，请使用：")
        print(f"  curl -X POST http://localhost:9002/pipeline/v2/process \\")
        print(f"    -H \"Content-Type: application/json\" \\")
        print(f"    -d '{{")
        print(f"      \"sessionId\":\"test_session_002\",")
        print(f"      \"attemptIndex\":0,")
        print(f"      \"templateCode\":\"{template_code}\",")
        print(f"      \"versionSemver\":\"{version_semver}\",")
        print(f"      \"downloadUrl\":\"{download_url}\",")
        print(f"      \"checksumSha256\":\"{checksum_sha256}\",")
        print(f"      \"rawPath\":\"{raw_path or 'D:/path/to/raw/image.jpg'}\"")
        print(f"    }}'")
        
    except TemplateDownloadError as e:
        print()
        print("❌ 模板下载失败")
        print(f"   错误: {e}")
        print()
        print("可能的原因：")
        print("  1. 下载 URL 不可访问")
        print("  2. 网络连接问题")
        print("  3. 服务器返回非 200 状态码")
        sys.exit(1)
        
    except TemplateChecksumMismatch as e:
        print()
        print("❌ 模板校验和不匹配")
        print(f"   错误: {e}")
        print()
        print("可能的原因：")
        print("  1. 提供的 checksumSha256 不正确")
        print("  2. 下载的文件被损坏或修改")
        sys.exit(1)
        
    except TemplateExtractError as e:
        print()
        print("❌ 模板解压失败")
        print(f"   错误: {e}")
        print()
        print("可能的原因：")
        print("  1. 下载的文件不是有效的 ZIP 文件")
        print("  2. ZIP 文件损坏")
        sys.exit(1)
        
    except TemplateInvalidError as e:
        print()
        print("❌ 模板无效")
        print(f"   错误: {e}")
        print()
        print("可能的原因：")
        print("  1. 解压后的目录中缺少 manifest.json")
        sys.exit(1)
        
    except Exception as e:
        print()
        print(f"❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    sys.exit(0)
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("   请确保在正确的环境中运行（已安装依赖）")
    print("   建议：cd D:\\workspace\\image-pipeline && python scripts/test_template_download_only.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
