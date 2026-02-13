# TemplateResolver 完整实现总结

## ✅ 已完成功能

### 1. 下载功能 (`_ensure_downloaded`)

**实现**:
- 使用 `requests.get()` 流式下载
- 超时设置：连接超时 5 秒，读取超时 30 秒
- 临时文件路径：`{final_dir.parent}/{checksum}.zip.tmp`
- 错误处理：下载失败时清理临时文件

**代码**:
```python
response = requests.get(
    self.download_url,
    stream=True,
    timeout=(5, 30)
)
```

---

### 2. SHA256 校验和计算 (`_sha256_file`)

**实现**:
- 使用 `hashlib.sha256()` 计算
- 分块读取文件（4KB 块），避免大文件内存问题
- 返回小写十六进制字符串

**代码**:
```python
sha256_hash = hashlib.sha256()
with open(file_path, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
return sha256_hash.hexdigest().lower()
```

---

### 3. 校验和验证 (`_validate_checksum`)

**实现**:
- 计算下载文件的 SHA256
- 与提供的 `checksumSha256` 对比（不区分大小写）
- 不匹配时抛出 `TemplateChecksumMismatch`

**代码**:
```python
calculated_checksum = self._sha256_file(zip_path)
expected_checksum = self.checksum.lower()

if calculated_checksum != expected_checksum:
    raise TemplateChecksumMismatch(...)
```

---

### 4. 解压功能 (`_extract_zip`)

**实现**:
- 解压到临时目录：`{final_dir}.tmp/`
- 校验 `manifest.json` 存在
- 如果不存在，抛出 `TemplateInvalidError`
- 错误处理：解压失败时清理临时目录

**代码**:
```python
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_tmp_dir)

manifest_path = extract_tmp_dir / "manifest.json"
if not manifest_path.exists():
    raise TemplateInvalidError(...)
```

---

### 5. 原子切换 (`os.replace`)

**实现**:
- 在 `resolve()` 方法中使用 `os.replace()` 原子切换
- 从临时目录切换到最终目录
- 确保不会产生半成品目录

**代码**:
```python
os.replace(extract_tmp_dir, self.final_dir)
```

---

### 6. 清理临时文件 (`try/finally`)

**实现**:
- 使用 `try/finally` 确保临时文件被清理
- 清理临时 zip 文件：`{checksum}.zip.tmp`
- 清理临时解压目录：`{final_dir}.tmp/`
- 忽略清理错误（避免掩盖主要错误）

**代码**:
```python
try:
    # 下载、校验、解压逻辑
    ...
finally:
    # 清理临时文件
    if zip_tmp_path and zip_tmp_path.exists():
        zip_tmp_path.unlink()
    if extract_tmp_dir and extract_tmp_dir.exists():
        shutil.rmtree(extract_tmp_dir)
```

---

## 🔍 完整流程

```
resolve()
  ↓
Step 1: 检查缓存命中
  ├─ manifest.json 存在? → 返回 final_dir
  └─ 不存在 → 继续
  ↓
Step 2: 下载 zip
  ├─ _ensure_downloaded()
  │   └─ requests.get() → {checksum}.zip.tmp
  ↓
Step 3: 校验 SHA256
  ├─ _sha256_file() 计算
  ├─ _validate_checksum() 对比
  └─ 不匹配 → TemplateChecksumMismatch
  ↓
Step 4: 解压到临时目录
  ├─ _extract_zip()
  │   ├─ 解压到 {final_dir}.tmp/
  │   └─ 校验 manifest.json 存在
  ↓
Step 5: 原子切换
  ├─ os.replace(tmp_dir, final_dir)
  ↓
Step 6: 清理临时文件
  └─ finally: 清理 zip.tmp 和 tmp_dir
  ↓
返回 final_dir
```

---

## 🧪 测试方法

### 方法 1：运行测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_template_resolver_download.py
```

**前提条件**:
1. HTTP 服务器运行在 `http://127.0.0.1:9000`
2. 提供文件 `tpl_001_v0.1.1.zip`
3. 文件的 SHA256 校验和为 `f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d`

**预期输出**:
```
============================================================
测试 TemplateResolver 下载、校验、解压功能
============================================================

开始解析模板...
✅ 模板解析成功！
   模板目录: D:\workspace\image-pipeline\app\data\_templates\tpl_001\0.1.1\f288dad7...

✅ 模板目录存在
✅ manifest.json 存在
✅ manifest.json 格式正确

============================================================
测试缓存命中（第二次调用）
============================================================

✅ 缓存命中成功！
```

---

### 方法 2：使用 Python 代码测试

```python
from app.services.template_resolver import TemplateResolver

resolver = TemplateResolver(
    template_code="tpl_001",
    version="0.1.1",
    download_url="http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
    checksum="f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
)

# 第一次调用：下载和解压
template_dir = resolver.resolve()
print(f"模板目录: {template_dir}")

# 第二次调用：缓存命中
template_dir2 = resolver.resolve()
print(f"缓存命中: {template_dir2}")
assert template_dir == template_dir2
```

---

### 方法 3：启动本地 HTTP 服务器测试

#### Step 1: 准备测试文件

```powershell
# 创建测试目录
mkdir test_template
cd test_template

# 创建 manifest.json
echo {"outputWidth": 1800, "outputHeight": 1200} > manifest.json

# 创建 zip 文件
Compress-Archive -Path * -DestinationPath ..\tpl_001_v0.1.1.zip
cd ..
```

#### Step 2: 计算校验和

```powershell
# PowerShell
$hash = Get-FileHash tpl_001_v0.1.1.zip -Algorithm SHA256
echo $hash.Hash
```

#### Step 3: 启动 HTTP 服务器

```powershell
# 在包含 zip 文件的目录中
python -m http.server 9000
```

#### Step 4: 运行测试

```powershell
cd D:\workspace\image-pipeline
python scripts\test_template_resolver_download.py
```

---

## 📋 异常类说明

### TemplateDownloadError
**触发条件**: 下载失败（非 200 / 超时）
**示例**:
```python
raise TemplateDownloadError(
    f"Download timeout for {self.download_url}: {e}"
)
```

### TemplateChecksumMismatch
**触发条件**: SHA256 校验和不匹配
**示例**:
```python
raise TemplateChecksumMismatch(
    f"Checksum mismatch: expected {expected}, got {calculated}"
)
```

### TemplateExtractError
**触发条件**: 解压失败（无效 zip / 解压错误）
**示例**:
```python
raise TemplateExtractError(f"Invalid zip file: {zip_path}")
```

### TemplateInvalidError
**触发条件**: 解压后缺 manifest.json
**示例**:
```python
raise TemplateInvalidError(
    f"manifest.json not found in extracted template at {extract_tmp_dir}"
)
```

---

## ✅ 验证清单

- [x] 下载功能：使用 `requests.get()` 流式下载
- [x] 超时设置：连接 5 秒，读取 30 秒
- [x] SHA256 计算：分块读取，避免内存问题
- [x] 校验和验证：与提供的 checksum 对比
- [x] 解压功能：解压到临时目录
- [x] manifest.json 验证：解压后必须存在
- [x] 原子切换：使用 `os.replace()` 原子操作
- [x] 清理临时文件：`try/finally` 确保清理
- [x] 异常处理：清晰的异常类和错误信息

---

## 🔄 测试数据

**测试 URL**: `http://127.0.0.1:9000/tpl_001_v0.1.1.zip`

**测试 Checksum**: `f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d`

**预期结果**:
- 下载成功
- 校验和匹配
- 解压成功
- manifest.json 存在
- 缓存目录正确创建

---

## 📝 总结

**已完成**:
- ✅ 下载功能实现
- ✅ SHA256 校验和计算与验证
- ✅ 解压功能实现
- ✅ manifest.json 验证
- ✅ 原子切换实现
- ✅ 临时文件清理
- ✅ 异常处理完善

**当前状态**: 完整功能已实现，可以进行真实 URL 测试。
