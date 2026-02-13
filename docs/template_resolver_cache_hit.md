# TemplateResolver 缓存命中功能说明

## ✅ 已完成功能

### 1. 配置项添加

在 `app/config.py` 中添加了 `TEMPLATE_CACHE_DIR` 配置：

```python
TEMPLATE_CACHE_DIR: str = Field(
    default="app/data/_templates",
    validation_alias="TEMPLATE_CACHE_DIR",
)
```

**默认值**: `app/data/_templates`（相对于项目根目录）

**支持环境变量**: 可以通过环境变量 `TEMPLATE_CACHE_DIR` 覆盖

---

### 2. 缓存目录结构

**规则**: `{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/`

**示例**:
```
app/data/_templates/
  └── tpl_001/
      └── 0.1.1/
          └── f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d/
              ├── manifest.json
              └── assets/
                  └── ...
```

**好处**:
- checksum 变了自动新目录，不污染旧缓存
- 支持同一版本多次发布（URL 不变但内容变）
- 目录结构清晰，易于管理

---

### 3. 缓存命中逻辑

**实现位置**: `TemplateResolver.resolve()`

**逻辑**:
1. 计算最终模板目录：`{cache_dir}/{templateCode}/{version}/{checksum}/`
2. 检查 `{final_dir}/manifest.json` 是否存在
3. 如果存在 → **缓存命中**，直接返回目录路径
4. 如果不存在 → **缓存未命中**，抛出 `NotImplementedError`（下载功能待实现）

**代码**:
```python
def resolve(self) -> str:
    # Step 1: 检查缓存命中
    manifest_path = self.final_dir / "manifest.json"
    if manifest_path.exists():
        # 缓存命中，直接返回
        return str(self.final_dir.resolve())
    
    # Step 2: 缓存未命中，需要下载和解压
    raise NotImplementedError("Template download and extraction not yet implemented.")
```

---

## 🔍 原理说明

### 缓存命中机制

1. **目录结构设计**:
   - 使用 `{templateCode}/{version}/{checksum}` 三级目录结构
   - checksum 作为最后一级，确保内容变化时自动创建新目录

2. **缓存检查**:
   - 只检查 `manifest.json` 是否存在（不检查其他文件）
   - 如果存在，认为模板已完整，直接返回

3. **路径解析**:
   - 使用 `Path.resolve()` 返回绝对路径
   - 确保路径唯一且可访问

---

## 🧪 测试方法

### 方法 1：运行测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_template_resolver_cache_hit.py
```

**预期输出**:
```
============================================================
TemplateResolver 缓存命中功能测试
============================================================

============================================================
测试 1: 配置读取
============================================================
TEMPLATE_CACHE_DIR: app/data/_templates
✅ 配置读取正常

============================================================
测试 2: 缓存目录结构
============================================================
缓存根目录: D:\workspace\image-pipeline\app\data\_templates
最终模板目录: ...\tpl_001\0.1.1\f288dad7...
✅ 缓存目录结构正确

============================================================
测试 3: 缓存命中
============================================================
创建测试模板目录: ...
创建 manifest.json: ...
✅ 缓存命中，返回路径: ...
✅ 缓存命中功能正常

============================================================
测试 4: 缓存未命中
============================================================
✅ 缓存未命中时正确抛出 NotImplementedError

✅ 所有测试通过！
```

---

### 方法 2：手动验证

#### Step 1: 创建测试模板目录

```powershell
# 进入项目目录
cd D:\workspace\image-pipeline

# 创建模板目录结构
mkdir -p app\data\_templates\tpl_test\1.0.0\test_checksum_123

# 创建 manifest.json
echo {"outputWidth": 1800, "outputHeight": 1200} > app\data\_templates\tpl_test\1.0.0\test_checksum_123\manifest.json
```

#### Step 2: 测试缓存命中

```python
from app.services.template_resolver import TemplateResolver

resolver = TemplateResolver(
    template_code="tpl_test",
    version="1.0.0",
    download_url="http://example.com/template.zip",
    checksum="test_checksum_123",
)

# 应该直接返回，不访问网络
template_dir = resolver.resolve()
print(f"模板目录: {template_dir}")
# 输出: 模板目录: D:\workspace\image-pipeline\app\data\_templates\tpl_test\1.0.0\test_checksum_123
```

#### Step 3: 验证返回路径

```python
from pathlib import Path

template_path = Path(template_dir)
assert template_path.exists(), "模板目录不存在"
assert (template_path / "manifest.json").exists(), "manifest.json 不存在"
print("✅ 缓存命中验证成功")
```

---

### 方法 3: 单元测试

运行现有的单元测试：

```powershell
pytest tests/test_template_resolver.py -v
```

---

## 📋 验证清单

- [x] 配置项 `TEMPLATE_CACHE_DIR` 已添加
- [x] 缓存目录结构正确：`{cache_dir}/{templateCode}/{version}/{checksum}/`
- [x] 缓存命中逻辑正确：检查 `manifest.json` 存在即返回
- [x] 缓存未命中时抛出 `NotImplementedError`（下载功能待实现）
- [x] 路径解析正确：返回绝对路径

---

## 🔄 下一步

当前实现只支持**缓存命中**，下载和解压功能待实现：

1. **实现下载功能** (`_ensure_downloaded`)
   - 下载 zip 到临时文件
   - 处理超时和错误

2. **实现校验和验证** (`_validate_checksum`)
   - 计算 SHA256
   - 与提供的 checksum 对比

3. **实现解压功能** (`_extract_zip`)
   - 解压到临时目录
   - 原子切换到最终目录

4. **实现并发锁机制**
   - 防止同一模板并发重复下载

---

## 📝 总结

**已完成**:
- ✅ 配置项添加
- ✅ 缓存目录结构设计
- ✅ 缓存命中逻辑实现

**待实现**:
- ⏳ 下载功能
- ⏳ 校验和验证
- ⏳ 解压功能
- ⏳ 并发锁机制

**当前状态**: 基础骨架和缓存命中功能已完成，可以验证。
