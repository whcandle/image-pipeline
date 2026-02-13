# ManifestLoader Step 1 完成总结

## ✅ 已完成功能

### 1. 异常类定义

**文件**: `app/services/manifest_loader.py`

**异常类**:
- `ManifestLoadError`: Manifest 加载失败（文件不存在或 JSON 解析错误）
- `ManifestValidationError`: Manifest 验证失败（字段缺失、类型错误、数值非法）

---

### 2. ManifestLoader 类实现

#### 2.1 构造函数

```python
def __init__(self, template_dir: str):
    self.template_dir = Path(template_dir)
    self.manifest_path = self.template_dir / "manifest.json"
```

#### 2.2 load_manifest() 方法

**功能**: 读取 template_dir/manifest.json 并解析 JSON

**实现**:
- 检查文件是否存在
- 读取并解析 JSON
- 文件不存在或 JSON 错误抛出 `ManifestLoadError`

**代码**:
```python
def load_manifest(self) -> Dict[str, Any]:
    if not self.manifest_path.exists():
        raise ManifestLoadError(f"manifest.json not found at {self.manifest_path}")
    
    try:
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestLoadError(f"Failed to parse manifest.json: {e}") from e
    except Exception as e:
        raise ManifestLoadError(f"Error reading manifest.json: {e}") from e
    
    return manifest
```

#### 2.3 validate_manifest() 方法

**功能**: 校验必填字段

**校验清单（A. 顶层必填）**:
- ✅ manifestVersion == 1
- ✅ templateCode（非空字符串）
- ✅ versionSemver（非空字符串）
- ✅ output.width, output.height（正整数）
- ✅ output.format（可选，默认 "png"）
- ✅ assets.basePath（可选，默认 "assets"）
- ✅ compose.background（必填，字符串）
- ✅ compose.photos（必填，list，至少 1 个）
- ✅ compose.stickers（可选，list，可为空）

**验证逻辑**:
- 字段缺失 → 抛出 `ManifestValidationError`
- 字段类型错误 → 抛出 `ManifestValidationError`
- 数值非法（如 width <= 0）→ 抛出 `ManifestValidationError`

---

## 🧪 测试验证

### 运行测试脚本

```powershell
cd D:\workspace\image-pipeline
python scripts\test_manifest_loader_basic.py
```

**测试结果**:
- ✅ 正常模板 load 成功
- ✅ 手动改坏 JSON → 抛异常
- ✅ 文件不存在 → 抛异常
- ✅ 删字段能报错（5 个测试用例全部通过）
- ✅ 打印 manifest key

---

## 📋 验证清单

- [x] `__init__(template_dir: str)` 已实现
- [x] `load_manifest() -> dict` 已实现
- [x] `validate_manifest(manifest: dict) -> None` 已实现
- [x] 异常类 `ManifestLoadError` 已定义
- [x] 异常类 `ManifestValidationError` 已定义
- [x] 校验必填字段：manifestVersion==1、templateCode、versionSemver、output.width/height、compose.background、compose.photos（至少 1 项）
- [x] 正常模板 load 成功
- [x] 手动改坏 JSON → 抛异常
- [x] 删字段能报错

---

## 🔍 测试用例详情

### 测试 1: 正常模板 load 成功
- 创建有效的 manifest.json
- 调用 `load_manifest()` 成功
- 调用 `validate_manifest()` 通过

### 测试 2: 手动改坏 JSON → 抛异常
- 创建无效的 JSON 文件
- 调用 `load_manifest()` 抛出 `ManifestLoadError`

### 测试 3: 文件不存在 → 抛异常
- 不创建 manifest.json
- 调用 `load_manifest()` 抛出 `ManifestLoadError`

### 测试 4: 删字段能报错
测试了 5 个场景：
1. 缺少 manifestVersion → 抛出 `ManifestValidationError`
2. 缺少 templateCode → 抛出 `ManifestValidationError`
3. 缺少 compose.photos → 抛出 `ManifestValidationError`
4. compose.photos 为空列表 → 抛出 `ManifestValidationError`
5. output.width 为负数 → 抛出 `ManifestValidationError`

### 测试 5: 打印 manifest key
- 打印所有 manifest 键
- 验证结构正确

---

## 📝 代码变更总结

### 修改的文件

1. **app/services/manifest_loader.py**
   - 重构异常类（添加 `ManifestLoadError`）
   - 重命名方法：`load()` → `load_manifest()`
   - 重命名方法：`validate()` → `validate_manifest()`
   - 实现新的校验逻辑（按照新的校验清单）

### 新增的文件

1. **scripts/test_manifest_loader_basic.py**
   - 基础功能测试脚本

---

## ✅ 验收标准

根据需求，Step 1 的验收标准：

- [x] ✅ `__init__(template_dir: str)` 已实现
- [x] ✅ `load_manifest() -> dict` 已实现（读取并解析 JSON）
- [x] ✅ `validate_manifest(manifest: dict) -> None` 已实现（校验必填字段）
- [x] ✅ 异常类 `ManifestLoadError`, `ManifestValidationError` 已定义
- [x] ✅ 暂时不做路径 normalize、不做文件存在性校验
- [x] ✅ 验证：写一个脚本打印 manifest key，删字段能报错

**结论**: Step 1 已完成 ✅

---

## 🔄 下一步

Step 2: 实现路径 normalize（相对路径 → 绝对路径）
- 实现 `normalize()` 方法
- basePath 默认 assets
- 生成 backgroundAbsPath 和 stickerAbsPath

Step 3: 实现资源存在性校验（早失败）
- backgroundAbsPath 必须存在
- 每个 stickerAbsPath 必须存在（stickers 非空）
