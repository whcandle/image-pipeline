# TemplateResolver Step 1 完成总结

## ✅ 已完成任务

### 1. 配置项添加

**文件**: `app/config.py`

添加了 `TEMPLATE_CACHE_DIR` 配置项：
```python
TEMPLATE_CACHE_DIR: str = Field(
    default="app/data/_templates",
    validation_alias="TEMPLATE_CACHE_DIR",
)
```

**特点**:
- 默认值：`app/data/_templates`（相对于项目根目录）
- 支持环境变量覆盖：`TEMPLATE_CACHE_DIR`
- 自动解析相对路径为绝对路径

---

### 2. TemplateResolver 重构

**文件**: `app/services/template_resolver.py`

#### 2.1 构造函数更新

**新签名**:
```python
def __init__(
    self,
    template_code: str,
    version: str,
    download_url: str,
    checksum: str,  # 现在是必需的
    cache_dir: Optional[str] = None
):
```

**变化**:
- `checksum` 现在是必需参数（不再是 Optional）
- `cache_dir` 默认从 `settings.TEMPLATE_CACHE_DIR` 读取
- 自动解析相对路径为绝对路径

#### 2.2 缓存目录结构

**新规则**: `{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/`

**实现**:
```python
def _get_cache_dir(self) -> Path:
    return self.cache_dir / self.template_code / self.version / self.checksum
```

**好处**:
- checksum 变了自动新目录，不污染旧缓存
- 支持同一版本多次发布（URL 不变但内容变）

#### 2.3 缓存命中逻辑

**实现**:
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

**逻辑**:
1. 检查 `{final_dir}/manifest.json` 是否存在
2. 如果存在 → 缓存命中，直接返回绝对路径
3. 如果不存在 → 缓存未命中，抛出 `NotImplementedError`（下载功能待实现）

---

### 3. 异常类更新

**新增异常类**:
- `TemplateChecksumMismatch`: SHA256 校验和不匹配（替代 `ChecksumValidationError`）
- `TemplateInvalidError`: 模板无效（解压后缺 manifest.json）

**保留异常类**:
- `TemplateDownloadError`: 下载失败
- `TemplateExtractError`: 解压失败

---

### 4. TODO 占位

**已添加的方法占位**（带清晰的 docstring）:
- `_ensure_downloaded()`: 下载 zip 到临时文件
- `_sha256_file()`: 计算文件的 SHA256
- `_validate_checksum()`: 验证校验和
- `_extract_zip()`: 原子解压到最终目录

---

## 🧪 测试方法

### 快速验证（推荐）

#### 方法 1: 运行测试脚本

```powershell
cd D:\workspace\image-pipeline
python scripts\test_template_resolver_cache_hit.py
```

**注意**: 如果环境没有安装依赖，可以先安装：
```powershell
pip install pydantic-settings
```

#### 方法 2: 手动创建测试模板

```powershell
# 创建测试模板目录
mkdir -p app\data\_templates\tpl_test\1.0.0\test_checksum_123

# 创建 manifest.json
echo {"outputWidth": 1800, "outputHeight": 1200} > app\data\_templates\tpl_test\1.0.0\test_checksum_123\manifest.json
```

然后运行 Python 代码：
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
print(f"✅ 缓存命中: {template_dir}")
```

#### 方法 3: 运行单元测试

```powershell
pytest tests/test_template_resolver.py::test_template_resolver_init -v
pytest tests/test_template_resolver.py::test_template_resolver_cache_dir_creation -v
```

---

## 📋 验证清单

- [x] 配置项 `TEMPLATE_CACHE_DIR` 已添加
- [x] 构造函数接收 `cache_dir`（默认从配置读取）
- [x] 缓存目录规则：`{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/`
- [x] 缓存命中逻辑：检查 `manifest.json` 存在即返回
- [x] 缓存未命中时抛出 `NotImplementedError`
- [x] 下载和解压方法已添加 TODO 占位
- [x] 所有方法都有清晰的 docstring

---

## 🔍 原理说明

### 缓存命中机制

1. **目录结构设计**:
   ```
   app/data/_templates/
     └── {templateCode}/
         └── {version}/
             └── {checksum}/
                 ├── manifest.json
                 └── assets/...
   ```

2. **缓存检查**:
   - 只检查 `manifest.json` 是否存在
   - 如果存在，认为模板已完整，直接返回绝对路径
   - 如果不存在，需要下载和解压（待实现）

3. **路径解析**:
   - 使用 `Path.resolve()` 返回绝对路径
   - 确保路径唯一且可访问

---

## 📝 代码变更总结

### 修改的文件

1. **app/config.py**
   - 添加 `TEMPLATE_CACHE_DIR` 配置项

2. **app/services/template_resolver.py**
   - 重构构造函数（checksum 必需）
   - 更新缓存目录结构（包含 checksum）
   - 实现缓存命中逻辑
   - 添加下载/解压方法占位
   - 更新异常类

### 新增的文件

1. **scripts/test_template_resolver_cache_hit.py**
   - 缓存命中功能测试脚本

2. **docs/template_resolver_cache_hit.md**
   - 功能说明文档

---

## ✅ 验收标准

根据需求，Step 1 的验收标准：

- [x] ✅ 构造函数接收 `cache_dir`（默认从 `config.TEMPLATE_CACHE_DIR`）
- [x] ✅ 实现 `resolve(templateCode, versionSemver, downloadUrl, checksumSha256) -> template_dir`
- [x] ✅ 缓存目录规则：`{cache_dir}/{templateCode}/{versionSemver}/{checksumSha256}/`
- [x] ✅ 如果 `manifest.json` 已存在则直接返回目录
- [x] ✅ 下载与解压的 TODO/占位已留好，docstring 清晰
- [x] ✅ 验证：手动创建目录+manifest.json，resolve 直接返回

**结论**: Step 1 已完成 ✅

---

## 🔄 下一步

Step 2: 实现下载功能
- 实现 `_ensure_downloaded()` 方法
- 下载 zip 到临时文件
- 处理超时和错误
