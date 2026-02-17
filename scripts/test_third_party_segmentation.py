"""
测试 ThirdPartySegmentationProvider 的本地脚本

使用方法：
1. 准备一张测试图片（jpg/png）
2. 设置环境变量或修改脚本中的 API key
3. 运行：python scripts/test_third_party_segmentation.py <image_path> [api_key]

示例：
python scripts/test_third_party_segmentation.py test.jpg your_api_key
"""

import sys
import os
from pathlib import Path
from PIL import Image

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.segmentation.third_party_provider import (
    ThirdPartySegmentationProvider,
    SegmentationProviderError,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_third_party_segmentation.py <image_path> [api_key]")
        print("\nExample:")
        print("  python test_third_party_segmentation.py test.jpg your_api_key")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    api_key = sys.argv[2] if len(sys.argv) > 2 else os.getenv("REMOVEBG_API_KEY", "")
    
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    if not api_key:
        print("Error: API key not provided")
        print("  Set REMOVEBG_API_KEY environment variable or pass as argument")
        sys.exit(1)
    
    print(f"Testing ThirdPartySegmentationProvider with image: {image_path}")
    print(f"API Key: {api_key[:10]}...")
    
    # 准备 execution plan
    execution_plan = {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg",
        "auth": {
            "type": "api_key",
            "apiKey": api_key,
        },
        "timeoutMs": 30000,  # 30秒
        "params": {
            "size": "auto",
            "format": "png",
        },
    }
    
    # 创建 provider
    provider = ThirdPartySegmentationProvider()
    
    try:
        # 调用 API
        print("\nCalling remove.bg API...")
        result_image = provider.process(image_path, execution_plan)
        
        # 保存结果
        output_path = Path("test_output") / f"cutout_{image_path.stem}.png"
        output_path.parent.mkdir(exist_ok=True)
        result_image.save(output_path, format="PNG")
        
        print(f"\n[SUCCESS]")
        print(f"   Input: {image_path}")
        print(f"   Output: {output_path}")
        print(f"   Size: {result_image.size}")
        print(f"   Mode: {result_image.mode}")
        
        # 验证是 RGBA
        if result_image.mode == "RGBA":
            print("   [OK] Output is RGBA (transparent background)")
        else:
            print(f"   [WARNING] Output mode is {result_image.mode}, expected RGBA")
        
    except SegmentationProviderError as e:
        print(f"\n[ERROR] Segmentation failed:")
        print(f"   Error: {e}")
        if e.status_code:
            print(f"   Status Code: {e.status_code}")
        if e.response_summary:
            print(f"   Response: {e.response_summary}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
