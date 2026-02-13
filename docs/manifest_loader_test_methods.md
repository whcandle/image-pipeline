# ManifestLoader.to_runtime_spec() 测试方法

## 🚀 最简单测试方法

### 方法 1: 运行测试脚本（推荐，最快）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_manifest_loader_runtime_spec.py
```

**预期输出**:
```
============================================================
ManifestLoader.to_runtime_spec() 测试
============================================================

测试 1: 基本的 runtime spec 生成
[OK] runtime spec 生成成功
   模板代码: tpl_001
   版本: 0.1.1
   输出尺寸: 1800x1200
   输出格式: png
   背景路径: C:\...\template\assets\bg.png
[OK] 背景路径正确

测试 2: 默认值补全
[OK] output.format 默认值正确: png
[OK] photo.fit 默认值正确: cover
[OK] photo.z 默认值正确: 0
[OK] sticker.rotate 默认值正确: 0
[OK] sticker.opacity 默认值正确: 1.0
[OK] sticker.z 默认值正确: 0

测试 3: stickers 的两种 src 规则
[OK] sticker1 路径正确（assets/ 开头）
[OK] sticker2 路径正确（相对 basePath）

测试 4: 打印 runtime spec
Runtime Spec:
{
  "manifestVersion": 1,
  "templateCode": "tpl_001",
  ...
}

[OK] 所有测试通过！
```

---

### 方法 2: 运行 pytest 测试（自动测试）

```powershell
pytest tests/test_manifest_loader_runtime_spec.py -v
```

**预期输出**:
```
test_manifest_loader_runtime_spec.py::test_runtime_spec_basic PASSED
test_manifest_loader_runtime_spec.py::test_runtime_spec_default_values PASSED
test_manifest_loader_runtime_spec.py::test_stickers_src_rules PASSED
test_manifest_loader_runtime_spec.py::test_runtime_spec_all_paths_absolute PASSED
test_manifest_loader_runtime_spec.py::test_runtime_spec_custom_base_path PASSED

5 passed
```

---

### 方法 3: 手动测试（最简单）

```python
from app.services.manifest_loader import ManifestLoader
import json

# 假设 template_dir 是 TemplateResolver.resolve() 的返回值
template_dir = "D:/workspace/image-pipeline/app/data/_templates/tpl_001/0.1.1/checksum"

loader = ManifestLoader(template_dir)
manifest = loader.load_manifest()
loader.validate_manifest(manifest)
runtime_spec = loader.to_runtime_spec(manifest)

# 打印 runtime spec
print(json.dumps(runtime_spec, indent=2, ensure_ascii=False))

# 验证路径都是绝对路径
from pathlib import Path
bg_path = Path(runtime_spec["background"]["path"])
print(f"背景路径: {bg_path}")
print(f"是绝对路径: {bg_path.is_absolute()}")
print(f"文件存在: {bg_path.exists()}")
```

---

## 📋 验证要点

### 1. 路径都是绝对路径
- ✅ 背景路径是绝对路径
- ✅ 所有贴纸路径都是绝对路径

### 2. 默认值补全
- ✅ output.format 默认 "png"
- ✅ photo.fit 默认 "cover"
- ✅ photo.z 默认 0
- ✅ sticker.rotate 默认 0
- ✅ sticker.opacity 默认 1.0
- ✅ sticker.z 默认 0

### 3. stickers 的两种 src 规则
- ✅ `src="assets/sticker.png"` → 绝对路径正确
- ✅ `src="sticker.png"` → 绝对路径正确（相对于 basePath）

---

## 🎯 快速验证命令

```powershell
# 运行测试脚本（最快）
python scripts\test_manifest_loader_runtime_spec.py

# 运行 pytest（自动测试）
pytest tests/test_manifest_loader_runtime_spec.py -v -q
```
