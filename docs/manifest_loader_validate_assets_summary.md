# ManifestLoader.validate_assets() 实现总结

## ✅ 已完成功能

### 1. validate_assets() 方法实现

**功能**: 校验资源文件是否存在（早失败）

**实现逻辑**:

1. **校验 background 文件存在**
   ```python
   background_path = Path(runtime_spec["background"]["path"])
   if not background_path.exists():
       raise ManifestValidationError(
           f"Background file not found: {background_path}"
       )
   ```

2. **校验每个 sticker 文件存在**
   ```python
   for sticker in runtime_spec.get("stickers", []):
       sticker_path = Path(sticker["path"])
       if not sticker_path.exists():
           raise ManifestValidationError(
               f"Sticker file not found: {sticker_path} (sticker id: {sticker.get('id', 'unknown')})"
           )
   ```

**异常处理**:
- 如果资源文件不存在，抛出 `ManifestValidationError`
- 错误信息包含文件路径，便于调试

---

## 📋 测试文件

### 1. 测试脚本：`scripts/test_manifest_loader.py`

**功能**:
- 使用 `TemplateResolver` 获取 `template_dir`
- 调用 `ManifestLoader` 加载 runtime spec
- 测试正常模板：所有资源文件存在，应该通过校验
- 测试背景文件不存在：应该早失败并输出清晰错误
- 测试贴纸文件不存在：应该早失败并输出清晰错误

**测试用例**:
1. `test_normal_template()`: 正常模板（应该通过所有校验）
2. `test_missing_background()`: 背景文件不存在（应该早失败）
3. `test_missing_sticker()`: 贴纸文件不存在（应该早失败）

---

### 2. pytest 测试：`tests/test_manifest_loader_validate_assets.py`

**功能**:
- 自动测试资源存在性校验功能
- 使用 mock 模拟 HTTP 下载，不依赖真实服务器

**测试用例**:
1. `test_validate_assets_normal_template`: 正常模板，所有资源文件存在
2. `test_validate_assets_missing_background`: 背景文件不存在
3. `test_validate_assets_missing_sticker`: 贴纸文件不存在
4. `test_validate_assets_multiple_stickers_one_missing`: 多个贴纸，其中一个不存在

---

## 🧪 测试方法

### 方法 1: 运行测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_manifest_loader.py
```

**预期输出**:
```
============================================================
ManifestLoader 完整流程测试（包括资源存在性校验）
============================================================

============================================================
测试 1: 正常模板（应该通过所有校验）
============================================================
[OK] TemplateResolver 解析成功: C:\...\template_dir
[OK] 资源存在性校验通过
[OK] 背景文件存在: C:\...\assets\bg.png
[OK] photos 数量: 1
[OK] 所有贴纸文件存在: 1 个

[OK] 测试 1 通过：正常模板通过所有校验

============================================================
测试 2: 背景文件不存在（应该早失败）
============================================================
[OK] TemplateResolver 解析成功: C:\...\template_dir
[OK] 正确抛出 ManifestValidationError: Background file not found: C:\...\nonexistent_bg.png
[OK] 错误信息清晰: Background file not found: C:\...\nonexistent_bg.png

[OK] 测试 2 通过：背景文件不存在时早失败

============================================================
测试 3: 贴纸文件不存在（应该早失败）
============================================================
[OK] TemplateResolver 解析成功: C:\...\template_dir
[OK] 正确抛出 ManifestValidationError: Sticker file not found: C:\...\nonexistent_sticker.png (sticker id: s1)
[OK] 错误信息清晰: Sticker file not found: C:\...\nonexistent_sticker.png (sticker id: s1)

[OK] 测试 3 通过：贴纸文件不存在时早失败

============================================================
[OK] 所有测试通过！
============================================================
```

---

### 方法 2: 运行 pytest 测试（自动测试）

```powershell
pytest tests/test_manifest_loader_validate_assets.py -v
```

**预期输出**:
```
test_manifest_loader_validate_assets.py::test_validate_assets_normal_template PASSED
test_manifest_loader_validate_assets.py::test_validate_assets_missing_background PASSED
test_manifest_loader_validate_assets.py::test_validate_assets_missing_sticker PASSED
test_manifest_loader_validate_assets.py::test_validate_assets_multiple_stickers_one_missing PASSED

4 passed
```

---

### 方法 3: 手动测试

```python
from app.services.manifest_loader import ManifestLoader, ManifestValidationError
from pathlib import Path

# 假设 template_dir 是 TemplateResolver.resolve() 的返回值
loader = ManifestLoader(template_dir)
manifest = loader.load_manifest()
loader.validate_manifest(manifest)
runtime_spec = loader.to_runtime_spec(manifest)

# 校验资源存在性
try:
    loader.validate_assets(runtime_spec)
    print("✅ 所有资源文件存在")
except ManifestValidationError as e:
    print(f"❌ 资源文件不存在: {e}")
```

---

## 📋 验证清单

- [x] 实现 `validate_assets(runtime_spec)` 方法
- [x] 校验 background 文件存在
- [x] 校验每个 sticker 文件存在
- [x] 如果资源文件不存在，抛出 `ManifestValidationError`
- [x] 错误信息包含文件路径
- [x] 测试脚本：正常模板通过
- [x] 测试脚本：背景文件不存在时早失败
- [x] 测试脚本：贴纸文件不存在时早失败
- [x] pytest 测试：4 个测试用例

---

## 🔍 错误信息示例

### 背景文件不存在
```
ManifestValidationError: Background file not found: D:\...\template\assets\nonexistent_bg.png
```

### 贴纸文件不存在
```
ManifestValidationError: Sticker file not found: D:\...\template\assets\nonexistent_sticker.png (sticker id: s1)
```

---

## ✅ 验收标准

根据需求，Step 3 的验收标准：

- [x] ✅ 实现 `validate_assets(runtime_spec)` 方法
- [x] ✅ backgroundAbsPath 必须存在，否则抛 `ManifestValidationError`（信息里带路径）
- [x] ✅ 每个 stickerAbsPath 必须存在，否则抛 `ManifestValidationError`
- [x] ✅ 测试脚本：使用 `TemplateResolver` 返回的 `template_dir`
- [x] ✅ 测试脚本：调用 `ManifestLoader` 加载 runtime spec
- [x] ✅ 测试脚本：assert background 文件存在、photos 数量>=1
- [x] ✅ 测试脚本：刻意把 compose.background 改成不存在的文件名时，脚本能早失败并输出清晰错误
- [x] ✅ 验证：正常模板通过
- [x] ✅ 验证：改错路径早失败

**结论**: Step 3 已完成 ✅

---

## 🔄 下一步

Step 4: 集成所有模块到 `/pipeline/v2/process` 路由，完成真实的图像处理流程。

---

## 📊 测试结果

**测试脚本**: ✅ 3 个测试用例全部通过
- test_normal_template: 正常模板通过所有校验
- test_missing_background: 背景文件不存在时早失败
- test_missing_sticker: 贴纸文件不存在时早失败

**pytest 测试**: ✅ 4 个测试用例全部通过
- test_validate_assets_normal_template
- test_validate_assets_missing_background
- test_validate_assets_missing_sticker
- test_validate_assets_multiple_stickers_one_missing
