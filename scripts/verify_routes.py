"""
验证路由是否正确注册

运行此脚本可以检查：
1. 所有路由是否正确导入
2. v1 和 v2 路由是否都已注册
3. 服务是否能正常启动（不实际启动，只检查导入）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.main import app
    
    print("✅ 成功导入 app.main")
    print(f"✅ FastAPI 应用已创建: {app.title} v{app.version}")
    print()
    
    # 检查路由
    print("📋 已注册的路由:")
    print("-" * 60)
    
    routes_found = {
        "v1": False,
        "v2": False,
        "health": False
    }
    
    for route in app.routes:
        route_path = getattr(route, "path", None)
        route_methods = getattr(route, "methods", set())
        
        if route_path:
            # 格式化显示
            methods_str = ", ".join(sorted(route_methods)) if route_methods else "N/A"
            print(f"  {methods_str:15} {route_path}")
            
            # 检查关键路由
            if "/pipeline/v1/process" in route_path:
                routes_found["v1"] = True
            if "/pipeline/v2/process" in route_path:
                routes_found["v2"] = True
            if "/health" in route_path or "/healthz" in route_path:
                routes_found["health"] = True
    
    print()
    print("✅ 路由检查结果:")
    print("-" * 60)
    print(f"  /pipeline/v1/process: {'✅ 已注册' if routes_found['v1'] else '❌ 未找到'}")
    print(f"  /pipeline/v2/process: {'✅ 已注册' if routes_found['v2'] else '❌ 未找到'}")
    print(f"  /health:              {'✅ 已注册' if routes_found['health'] else '⚠️  未找到（可选）'}")
    
    if routes_found["v1"] and routes_found["v2"]:
        print()
        print("🎉 所有路由已正确注册！")
        sys.exit(0)
    else:
        print()
        print("⚠️  部分路由未找到，请检查路由配置")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("   请确保在项目根目录运行此脚本")
    sys.exit(1)
except Exception as e:
    print(f"❌ 验证过程中出错: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
