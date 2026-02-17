# PlatformClient 测试指南

## 📋 功能概述

`PlatformClient` 用于调用 platform API 的 resolve 接口，获取 segmentation 的 execution plan。

**关键特性：**
- 仅在 `needs_segmentation=true` 时调用
- 失败时记录错误但不崩溃（降级处理）
- 将 resolve 结果写入 `response.notes`

## 🧪 测试方法

### 方法 1: 运行 pytest 自动化测试（推荐）

```bash
cd D:\workspace\image-pipeline

# 运行 PlatformClient 单元测试
pytest tests/test_platform_client.py -v

# 运行集成测试（v2 process 中的集成）
pytest tests/test_platform_resolve_integration.py -v

# 运行所有 platform 相关测试
pytest tests/test_platform*.py -v
```

**测试覆盖：**

1. ✅ `test_platform_client_resolve_success`: resolve 成功
2. ✅ `test_platform_client_resolve_http_error`: HTTP 错误处理
3. ✅ `test_platform_client_resolve_timeout`: 超时处理
4. ✅ `test_platform_resolve_success`: v2 process 中 resolve 成功
5. ✅ `test_platform_resolve_failed`: v2 process 中 resolve 失败（不崩溃）
6. ✅ `test_platform_resolve_not_called_when_not_needed`: needs_segmentation=false 时不调用

---

### 方法 2: 通过 API 手动测试

#### 场景 1: Platform 正常，resolve 成功

**准备：**
1. 确保 platform 服务运行在 `http://localhost:9000`（或设置 `PLATFORM_BASE_URL`）
2. 使用 `source=cutout` 且 `rules.segmentation.enabled=true` 的模板

**调用 API：**
```bash
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{
    "templateCode": "tpl_002",
    "versionSemver": "0.1.2",
    "downloadUrl": "http://127.0.0.1:9000/tpl_002_v0.1.2.zip",
    "checksumSha256": "f909e74b3432be726507abd70f794d2259f3ab199ef609557d45ade377b6f126",
    "rawPath": "D:/path/to/raw.jpg"
  }'
```

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": true}
    },
    {
      "code": "SEG_RESOLVED_PROVIDER",
      "details": {
        "providerCode": "removebg",
        "endpoint": "https://api.remove.bg/v1.0/removebg"
      }
    }
  ]
}
```

---

#### 场景 2: Platform 停掉，resolve 失败

**准备：**
1. 停止 platform 服务（或设置错误的 `PLATFORM_BASE_URL`）
2. 使用 `source=cutout` 且 `rules.segmentation.enabled=true` 的模板

**调用 API：**（同上）

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": true}
    },
    {
      "code": "SEG_RESOLVE_FAILED",
      "details": {
        "error": "Platform resolve API call failed: ...",
        "value": true
      }
    }
  ]
}
```

**关键验证点：**
- ✅ `ok=true`（流程不崩溃）
- ✅ `outputs.previewUrl` 和 `outputs.finalUrl` 存在（仍能出图）
- ✅ `SEG_RESOLVE_FAILED` 在 notes 中

---

#### 场景 3: needs_segmentation=false，不调用 resolve

**准备：**
- 使用 `source=raw` 的模板，或 `source=cutout` 但 `rules.segmentation.enabled=false`

**调用 API：**（同上）

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": false}
    }
  ]
}
```

**关键验证点：**
- ✅ `SEG_RESOLVED_PROVIDER` **不在** notes 中
- ✅ `SEG_RESOLVE_FAILED` **不在** notes 中
- ✅ 流程正常完成

---

## 🔧 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# Platform API 基础 URL
PLATFORM_BASE_URL=http://localhost:9000

# Platform API 请求超时（毫秒）
PLATFORM_TIMEOUT_MS=5000
```

### 默认值

- `PLATFORM_BASE_URL`: `http://localhost:9000`
- `PLATFORM_TIMEOUT_MS`: `5000` (5秒)

---

## 📝 请求/响应格式

### Platform Resolve 请求

```json
{
  "capability": "segmentation",
  "templateCode": "tpl_002",
  "versionSemver": "0.1.2",
  "prefer": ["removebg", "rembg"],
  "constraints": {
    "timeoutMs": 6000
  },
  "hintParams": {
    "output": "rgba",
    "quality": "high"  // 可选
  }
}
```

### Platform Resolve 响应

```json
{
  "providerCode": "removebg",
  "endpoint": "https://api.remove.bg/v1.0/removebg",
  "timeoutMs": 5000
}
```

---

## ✅ 验证清单

### 场景 1: Platform 正常
- [x] `needs_segmentation=true` 时调用 resolve
- [x] `notes` 有 `SEG_RESOLVED_PROVIDER`
- [x] `providerCode` 和 `endpoint` 正确写入 notes
- [x] 流程正常完成（ok=true）

### 场景 2: Platform 停掉
- [x] `needs_segmentation=true` 时调用 resolve
- [x] resolve 失败被捕获，不崩溃
- [x] `notes` 有 `SEG_RESOLVE_FAILED`
- [x] 流程仍能完成（ok=true，能出图）

### 场景 3: 不需要 segmentation
- [x] `needs_segmentation=false` 时不调用 resolve
- [x] `notes` 没有 `SEG_RESOLVED_PROVIDER` 和 `SEG_RESOLVE_FAILED`
- [x] 流程正常完成

---

## 🔍 调试技巧

### 1. 检查 resolve 是否被调用

在 `app/routers/process.py` 中添加日志：

```python
if needs_segmentation:
    print(f"[process_v2] Calling platform resolve...")
    # ...
```

### 2. 检查 resolve 请求参数

在 `app/clients/platform_client.py` 中添加日志：

```python
def resolve(self, ...):
    print(f"[PlatformClient] Resolve request: {request_body}")
    # ...
```

### 3. 检查环境变量

```bash
# PowerShell
$env:PLATFORM_BASE_URL
$env:PLATFORM_TIMEOUT_MS

# 或在 Python 中
from app.config import settings
print(settings.PLATFORM_BASE_URL)
print(settings.PLATFORM_TIMEOUT_MS)
```

---

## 📚 相关文件

- `app/clients/platform_client.py`: PlatformClient 实现
- `app/routers/process.py`: v2 process 集成（调用 resolve）
- `app/config.py`: 配置管理（环境变量）
- `tests/test_platform_client.py`: 单元测试
- `tests/test_platform_resolve_integration.py`: 集成测试

---

## 🚨 常见问题

### Q: resolve 失败后，流程还能继续吗？

**A:** 是的。`PlatformResolveError` 被捕获后，只记录到 notes，不中断流程。后续步骤可以基于 `SEG_RESOLVE_FAILED` 做降级处理。

### Q: 如何修改 resolve 的超时时间？

**A:** 设置环境变量 `PLATFORM_TIMEOUT_MS`（单位：毫秒），或在代码中创建 `PlatformClient` 时传入 `timeout_ms` 参数。

### Q: resolve 返回的 endpoint 在哪里使用？

**A:** 当前只记录到 notes，后续步骤（实际调用抠图 API）会使用这个 endpoint。
