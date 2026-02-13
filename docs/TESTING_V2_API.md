# Pipeline V2 API 测试指南

本文档说明如何测试 `/pipeline/v2/process` 接口。

## 快速测试方法

### 方法 1: 使用 pytest 自动测试（推荐）

```bash
cd D:\workspace\image-pipeline

# 运行所有 V2 API 测试
pytest tests/test_process_api_v2.py -v

# 运行特定测试
pytest tests/test_process_api_v2.py::test_process_v2_success -v
pytest tests/test_process_api_v2.py::test_process_v2_checksum_mismatch -v
pytest tests/test_process_api_v2.py::test_process_v2_bg_missing -v
```

### 方法 2: 使用 curl 手动测试

#### 成功测试

```bash
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "downloadUrl": "http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
    "checksumSha256": "f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
    "rawPath": "D:/path/to/raw/image.jpg"
  }'
```

**预期响应**:
```json
{
  "ok": true,
  "jobId": "job_...",
  "template": {...},
  "outputs": {
    "previewUrl": "http://localhost:9002/files/preview/.../preview.png",
    "finalUrl": "http://localhost:9002/files/final/.../final.png"
  },
  "timing": {...},
  "warnings": [],
  "notes": [
    {
      "code": "PREVIEW_EQUALS_FINAL",
      "message": "..."
    }
  ]
}
```

#### 校验和不匹配测试

```bash
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "downloadUrl": "http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
    "checksumSha256": "wrong_checksum_0000000000000000000000000000000000000000000000000000000000000000",
    "rawPath": "D:/path/to/raw/image.jpg"
  }'
```

**预期响应**:
```json
{
  "ok": false,
  "jobId": "job_...",
  "error": {
    "code": "TEMPLATE_CHECKSUM_MISMATCH",
    "message": "...",
    "retryable": false,
    "detail": {
      "expected": "wrong_checksum_...",
      "actual": "..."
    }
  },
  "timing": {...},
  "notes": [...]
}
```

#### 背景文件缺失测试

需要先准备一个缺少背景文件的模板，然后调用接口。

## 测试用例说明

### 1. test_process_v2_success

**测试目标**: 验证成功处理流程

**断言**:
- `ok=true`
- `previewUrl` 和 `finalUrl` 存在且非空
- `notes` 中包含 `PREVIEW_EQUALS_FINAL`

### 2. test_process_v2_checksum_mismatch

**测试目标**: 验证校验和不匹配的错误处理

**断言**:
- `ok=false`
- `error.code` 为 `TEMPLATE_CHECKSUM_MISMATCH`
- `error.retryable=false`
- `error.detail` 包含 `expected` 和 `actual`

### 3. test_process_v2_bg_missing

**测试目标**: 验证背景文件缺失的错误处理

**断言**:
- `ok=false`
- `error.code` 为 `ASSET_NOT_FOUND`
- `error.retryable=false`

### 4. test_process_v2_download_failed

**测试目标**: 验证模板下载失败的错误处理

**断言**:
- `ok=false`
- `error.code` 为 `TEMPLATE_DOWNLOAD_FAILED`
- `error.retryable=true`

### 5. test_process_v2_render_failed

**测试目标**: 验证渲染失败的错误处理

**断言**:
- `ok=false`
- `error.code` 为 `RENDER_FAILED`
- `error.retryable=false`

## 错误码映射

| 异常类型 | 错误码 | retryable |
|---------|--------|-----------|
| TemplateDownloadError | TEMPLATE_DOWNLOAD_FAILED | true |
| TemplateChecksumMismatch | TEMPLATE_CHECKSUM_MISMATCH | false |
| TemplateExtractError | TEMPLATE_EXTRACT_ERROR | false |
| ManifestLoadError | MANIFEST_LOAD_ERROR | false |
| ManifestValidationError (资源缺失) | ASSET_NOT_FOUND | false |
| ManifestValidationError (结构错误) | MANIFEST_INVALID | false |
| RenderError | RENDER_FAILED | false |
| StorageError | STORE_FAILED | true |

## 注意事项

1. **所有错误都返回 200 状态码**：错误信息通过响应体的 `ok=false` 和 `error` 字段返回，不会抛出 500 错误。

2. **测试需要 mock**：由于测试需要模拟模板下载和文件系统操作，测试使用了 `monkeypatch` 来 mock 相关服务。

3. **临时文件清理**：测试使用 `tempfile.TemporaryDirectory` 自动清理临时文件。

4. **真实环境测试**：如果要测试真实环境，需要：
   - 准备真实的模板 zip 文件
   - 准备真实的原始图像文件
   - 确保模板服务器可访问
