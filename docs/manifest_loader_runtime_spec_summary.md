# ManifestLoader.to_runtime_spec() 实现总结

## ✅ 已完成功能

### 1. to_runtime_spec() 方法实现

**功能**: 将 manifest 转换为 runtime spec（包含绝对路径）

**实现逻辑**:

1. **读取 basePath**（默认 "assets"）
   ```python
   base_path = "assets"
   if "assets" in manifest and "basePath" in manifest["assets"]:
       base_path = manifest["assets"]["basePath"]
   ```

2. **生成 background 的绝对路径**
   ```python
   background_rel = compose["background"]
   background_abs = str(self.template_dir / base_path / background_rel)
   ```

3. **处理 photos（补默认值）**
   - `fit`: 默认 "cover"
   - `z`: 默认 0

4. **处理 stickers（补默认值，并转换为绝对路径）**
   - 支持两种 src 规则：
     - 如果 `src` 以 `"assets/"` 开头：`abs = join(template_dir, src)`
     - 否则：`abs = join(template_dir, basePath, src)`
   - 补默认值：
     - `rotate`: 默认 0
     - `opacity`: 默认 1.0
     - `z`: 默认 0

5. **构建 runtime spec**
   ```python
   runtime_spec = {
       "manifestVersion": 1,
       "templateCode": "...",
       "versionSemver": "...",
       "output": {"width": ..., "height": ..., "format": "png"},
       "background": {"path": "绝对路径"},
       "photos": [...],
       "stickers": [...]
   }
   ```

---

## 📋 Runtime Spec 结构

### 输出格式

```json
{
  "manifestVersion": 1,
  "templateCode": "tpl_001",
  "versionSemver": "0.1.1",
  "output": {
    "width": 1800,
    "height": 1200,
    "format": "png"
  },
  "background": {
    "path": "D:\\...\\template\\assets\\bg.png"
  },
  "photos": [
    {
      "id": "p1",
      "source": "raw",
      "x": 100,
      "y": 200,
      "w": 800,
      "h": 900,
      "fit": "cover",
      "z": 0
    }
  ],
  "stickers": [
    {
      "id": "s1",
      "path": "D:\\...\\template\\assets\\sticker1.png",
      "x": 50,
      "y": 50,
      "w": 100,
      "h": 100,
      "rotate": 0,
      "opacity": 1.0,
      "z": 0
    }
  ]
}
```

---

## 🧪 测试验证

### 方法 1: 运行测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_manifest_loader_runtime_spec.py
```

**测试结果**:
- ✅ 基本的 runtime spec 生成
- ✅ 默认值补全
- ✅ stickers 的两种 src 规则
- ✅ 打印 runtime spec（所有路径都是绝对路径）

---

### 方法 2: 运行 pytest 测试

```powershell
pytest tests/test_manifest_loader_runtime_spec.py -v
```

**测试用例**:
- `test_runtime_spec_basic`: 基本的 runtime spec 生成
- `test_runtime_spec_default_values`: 默认值补全
- `test_stickers_src_rules`: stickers 的两种 src 规则
- `test_runtime_spec_all_paths_absolute`: 所有路径都是绝对路径
- `test_runtime_spec_custom_base_path`: 自定义 basePath

---

### 方法 3: 手动测试

```python
from app.services.manifest_loader import ManifestLoader

# 假设 template_dir 是 TemplateResolver.resolve() 的返回值
loader = ManifestLoader(template_dir)
manifest = loader.load_manifest()
loader.validate_manifest(manifest)
runtime_spec = loader.to_runtime_spec(manifest)

# 打印 runtime spec
import json
print(json.dumps(runtime_spec, indent=2, ensure_ascii=False))

# 验证路径都是绝对路径
from pathlib import Path
bg_path = Path(runtime_spec["background"]["path"])
assert bg_path.is_absolute(), "背景路径应该是绝对路径"

for sticker in runtime_spec["stickers"]:
    sticker_path = Path(sticker["path"])
    assert sticker_path.is_absolute(), "贴纸路径应该是绝对路径"
```

---

## 📋 验证清单

- [x] 读取 assets.basePath（默认 "assets"）
- [x] 生成 background 的绝对路径：`join(template_dir, basePath, compose.background)`
- [x] 处理 stickers 的两种 src 规则
  - [x] 如果 src 以 "assets/" 开头：`abs = join(template_dir, src)`
  - [x] 否则：`abs = join(template_dir, basePath, src)`
- [x] 输出 runtime spec dict
- [x] 包含 templateCode, versionSemver
- [x] 包含 output (width/height/format)
- [x] 包含 backgroundAbsPath
- [x] 包含 photos[]（补默认值 fit/z）
- [x] 包含 stickers[]（补默认值 rotate/opacity/z）
- [x] 所有路径都是绝对路径

---

## 🔍 路径拼接规则

### background 路径规则

**manifest 中**: `compose.background = "bg.png"`（相对 basePath）

**ManifestLoader 处理**: 
```python
background_abs = join(template_dir, basePath, background)
# 例如: D:\...\template\assets\bg.png
```

### sticker src 路径规则（兼容两种写法）

**规则 1**: `src` 以 `"assets/"` 开头
```python
# manifest: "src": "assets/sticker.png"
# 处理: abs = join(template_dir, "assets/sticker.png")
# 结果: D:\...\template\assets\sticker.png
```

**规则 2**: `src` 不以 `"assets/"` 开头
```python
# manifest: "src": "sticker.png"
# 处理: abs = join(template_dir, basePath, "sticker.png")
# 结果: D:\...\template\assets\sticker.png
```

---

## 📝 默认值补全

### photos 默认值
- `fit`: 默认 `"cover"`（如果未提供）
- `z`: 默认 `0`（如果未提供）

### stickers 默认值
- `rotate`: 默认 `0`（如果未提供）
- `opacity`: 默认 `1.0`（如果未提供）
- `z`: 默认 `0`（如果未提供）

### output 默认值
- `format`: 默认 `"png"`（如果未提供）

---

## ✅ 验收标准

根据需求，Step 2 的验收标准：

- [x] ✅ 实现 `to_runtime_spec(manifest: dict) -> dict`
- [x] ✅ 读取 assets.basePath（默认 "assets"）
- [x] ✅ 生成 background 的绝对路径
- [x] ✅ 处理 stickers 的两种 src 规则
- [x] ✅ 输出 runtime spec dict，包含所有必要字段
- [x] ✅ 为可选字段补默认值（fit/z/rotate/opacity）
- [x] ✅ 验证：打印 runtime spec，路径都正确

**结论**: Step 2 已完成 ✅

---

## 🔄 下一步

Step 3: 实现资源存在性校验（早失败）
- backgroundAbsPath 必须存在
- 每个 stickerAbsPath 必须存在（stickers 非空）

---

## 📊 测试结果

**脚本测试**: ✅ 所有测试通过（4/4）
- 基本的 runtime spec 生成
- 默认值补全
- stickers 的两种 src 规则
- 打印 runtime spec

**pytest 测试**: ✅ 5 个测试用例全部通过
- test_runtime_spec_basic
- test_runtime_spec_default_values
- test_stickers_src_rules
- test_runtime_spec_all_paths_absolute
- test_runtime_spec_custom_base_path
