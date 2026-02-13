"""
快速测试验证脚本：验证 TemplateResolver 和 RenderEngine 模块

使用方法：
    python scripts/quick_test_modules.py

这会测试：
1. TemplateResolver 的基本功能（不实际下载，只测试结构）
2. RenderEngine 的渲染功能（使用示例图像）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from app.services.template_resolver import TemplateResolver
from app.services.render_engine import RenderEngine


def test_template_resolver():
    """测试 TemplateResolver 初始化"""
    print("=" * 60)
    print("测试 TemplateResolver")
    print("=" * 60)
    
    resolver = TemplateResolver(
        template_code="tpl_001",
        version="0.1.0",
        download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        checksum="f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
    )
    
    print(f"✅ TemplateResolver 初始化成功")
    print(f"   - template_code: {resolver.template_code}")
    print(f"   - version: {resolver.version}")
    print(f"   - download_url: {resolver.download_url}")
    print(f"   - cache_dir: {resolver.cache_dir}")
    print(f"   - template_cache_path: {resolver.template_cache_path}")
    
    return True


def test_render_engine():
    """测试 RenderEngine 渲染功能"""
    print("\n" + "=" * 60)
    print("测试 RenderEngine")
    print("=" * 60)
    
    # 创建示例图像
    sample_image = Image.new("RGB", (200, 200), color=(255, 0, 0))  # 红色
    print(f"✅ 创建示例图像: {sample_image.size}, mode={sample_image.mode}")
    
    # 测试 1: 使用尺寸创建画布
    manifest1 = {
        "outputWidth": 800,
        "outputHeight": 600,
        "backgroundColor": (255, 255, 255, 255),
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    engine1 = RenderEngine(manifest1)
    canvas1 = engine1._create_canvas()
    print(f"✅ 从尺寸创建画布: {canvas1.size}, mode={canvas1.mode}")
    
    # 测试 2: 应用单个照片
    result1 = engine1._apply_single_photo(canvas1, sample_image.convert("RGBA"))
    print(f"✅ 应用单个照片: {result1.size}")
    
    # 测试 3: 使用 photos 配置
    manifest2 = {
        "outputWidth": 800,
        "outputHeight": 600,
        "photos": [
            {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
            {"x": 0.6, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FIT"},
        ],
    }
    
    engine2 = RenderEngine(manifest2)
    canvas2 = engine2._create_canvas()
    result2 = engine2.apply_photos(canvas2, manifest2["photos"], sample_image.convert("RGBA"))
    print(f"✅ 应用多个照片: {result2.size}")
    
    # 测试 4: 完整渲染
    result3 = engine2.render(sample_image.convert("RGBA"))
    print(f"✅ 完整渲染: {result3.size}")
    
    return True


def test_integration():
    """测试集成：模拟完整流程（不实际下载）"""
    print("\n" + "=" * 60)
    print("测试集成流程（模拟）")
    print("=" * 60)
    
    # 1. 创建 TemplateResolver（不实际下载）
    resolver = TemplateResolver(
        template_code="tpl_test",
        version="1.0.0",
        download_url="http://example.com/template.zip",
    )
    print(f"✅ TemplateResolver 创建: {resolver.template_code} v{resolver.version}")
    
    # 2. 创建 RenderEngine（使用模拟 manifest）
    manifest = {
        "outputWidth": 1800,
        "outputHeight": 1200,
        "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
        "cropMode": "FILL",
    }
    
    engine = RenderEngine(manifest, template_dir=str(resolver.template_cache_path))
    print(f"✅ RenderEngine 创建: canvas size={manifest['outputWidth']}x{manifest['outputHeight']}")
    
    # 3. 渲染图像
    sample_image = Image.new("RGB", (500, 500), color=(0, 255, 0))  # 绿色
    result = engine.render(sample_image.convert("RGBA"))
    print(f"✅ 渲染完成: {result.size}, mode={result.mode}")
    
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("快速模块测试验证")
    print("=" * 60)
    print()
    
    try:
        # 测试各个模块
        test_template_resolver()
        test_render_engine()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print()
        print("说明：")
        print("- TemplateResolver: 结构正确，可以处理模板下载和解压")
        print("- RenderEngine: 渲染逻辑正常，可以合成图像")
        print("- 集成测试: 模块可以协同工作")
        print()
        print("下一步：")
        print("1. 运行完整单元测试: pytest tests/test_template_resolver.py tests/test_render_engine.py -v")
        print("2. 实现 ManifestLoader 模块")
        print("3. 实现 StorageManager 模块")
        print("4. 在路由中集成所有模块")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
