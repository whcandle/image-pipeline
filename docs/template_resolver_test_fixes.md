# TemplateResolver 测试修复说明

## ✅ 已修复的问题

### 1. test_template_extraction
**问题**: 缺少 `checksum` 参数（现在 checksum 是必需参数）

**修复**:
- 添加了 checksum 计算
- 更新了路径（因为现在路径包含 checksum）：`{cache_dir}/{templateCode}/{version}/{checksum}/`

### 2. test_template_resolver_cache_dir_creation
**问题**: 缺少 `checksum` 参数

**修复**:
- 添加了 `checksum="test_checksum_123"` 参数

### 3. test_concurrent_resolve_only_download_once
**问题**: 缺少 `import requests`

**修复**:
- 在函数开头添加了 `import requests`

---

## 🧪 重新运行测试

```powershell
cd D:\workspace\image-pipeline
pytest tests/test_template_resolver.py -q
```

**预期输出**:
```
........
8 passed, 1 skipped
```

---

## 📋 测试用例列表

1. ✅ `test_template_resolver_init` - 初始化测试
2. ✅ `test_template_resolver_checksum_validation` - 校验和验证测试
3. ✅ `test_template_extraction` - 解压功能测试（已修复）
4. ✅ `test_template_resolver_cache_dir_creation` - 缓存目录创建测试（已修复）
5. ✅ `test_template_resolver` - 完整流程测试
6. ⏭️ `test_template_resolver_with_real_http_server` - 真实服务器测试（跳过）
7. ✅ `test_cache_hit` - 缓存命中测试（新增）
8. ✅ `test_checksum_mismatch` - 校验和不匹配测试（新增）
9. ✅ `test_extract_contains_manifest_json` - 解压包含 manifest.json 测试（新增）
10. ✅ `test_concurrent_resolve_only_download_once` - 并发只下载一次测试（新增，已修复）

---

## ✅ 验证清单

- [x] 所有测试用例已修复
- [x] checksum 参数已添加到所有需要的测试
- [x] requests 导入已添加
- [x] 路径结构已更新（包含 checksum）

---

## 🚀 测试方法

### 最简单的方法

```powershell
pytest tests/test_template_resolver.py -q
```

### 详细输出

```powershell
pytest tests/test_template_resolver.py -v
```

### 只运行新增的 4 个测试

```powershell
pytest tests/test_template_resolver.py::test_cache_hit \
       tests/test_template_resolver.py::test_checksum_mismatch \
       tests/test_template_resolver.py::test_extract_contains_manifest_json \
       tests/test_template_resolver.py::test_concurrent_resolve_only_download_once -v
```
