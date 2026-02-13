# Pipeline V2 API 响应示例

本文档提供 `/pipeline/v2/process` 接口的成功和失败响应 JSON 示例。

---

## 成功响应示例

### 完整成功响应

```json
{
  "ok": true,
  "jobId": "job_20240101_123456_abc123",
  "template": {
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "manifestVersion": 1
  },
  "outputs": {
    "previewUrl": "http://localhost:9002/files/preview/job_20240101_123456_abc123/preview.png",
    "finalUrl": "http://localhost:9002/files/final/job_20240101_123456_abc123/final.png"
  },
  "timing": {
    "totalMs": 1234,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 450
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 12
      },
      {
        "name": "RENDER",
        "ms": 650
      },
      {
        "name": "STORE",
        "ms": 122
      }
    ]
  },
  "warnings": [
    "Template checksum not provided, skipping validation",
    "Image resolution is lower than template recommended size"
  ],
  "notes": [
    {
      "code": "TEMPLATE_CACHED",
      "message": "Template was loaded from cache",
      "details": {
        "cachePath": "app/data/_templates/tpl_001/0.1.0/abc123...",
        "cacheAge": 3600
      }
    },
    {
      "code": "INFO_IMAGE_RESIZED",
      "message": "Raw image was resized to match template requirements",
      "details": {
        "originalSize": [1200, 1600],
        "resizedTo": [1024, 1024]
      }
    }
  ]
}
```

### 最小成功响应（无警告和提示）

```json
{
  "ok": true,
  "jobId": "job_20240101_123456_abc123",
  "template": {
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "manifestVersion": 1
  },
  "outputs": {
    "previewUrl": "http://localhost:9002/files/preview/job_20240101_123456_abc123/preview.png",
    "finalUrl": "http://localhost:9002/files/final/job_20240101_123456_abc123/final.png"
  },
  "timing": {
    "totalMs": 890,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 300
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 10
      },
      {
        "name": "RENDER",
        "ms": 500
      },
      {
        "name": "STORE",
        "ms": 80
      }
    ]
  },
  "warnings": [],
  "notes": []
}
```

---

## 失败响应示例

### 模板下载失败

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "TEMPLATE_DOWNLOAD_ERROR",
    "message": "Failed to download template from URL",
    "detail": {
      "downloadUrl": "http://example.com/template.zip",
      "statusCode": 404,
      "reason": "Template file not found"
    }
  },
  "timing": {
    "totalMs": 150,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 150
      }
    ]
  },
  "notes": [
    {
      "code": "ERROR_TEMPLATE_DOWNLOAD",
      "message": "Template download failed after 3 retries",
      "details": {
        "retryCount": 3,
        "lastError": "Connection timeout"
      }
    }
  ]
}
```

### 校验和不匹配

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "TEMPLATE_CHECKSUM_MISMATCH",
    "message": "Template checksum validation failed",
    "detail": {
      "expected": "abc123def456...",
      "actual": "xyz789uvw012...",
      "templateCode": "tpl_001",
      "versionSemver": "0.1.0"
    }
  },
  "timing": {
    "totalMs": 320,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 320
      }
    ]
  },
  "notes": [
    {
      "code": "WARN_CHECKSUM_MISMATCH",
      "message": "Downloaded template checksum does not match provided checksum",
      "details": {
        "action": "Template download was rejected for security reasons"
      }
    }
  ]
}
```

### Manifest 验证失败

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "MANIFEST_VALIDATION_ERROR",
    "message": "Manifest validation failed",
    "detail": {
      "reason": "Missing required field: compose.photos",
      "templateCode": "tpl_001",
      "versionSemver": "0.1.0"
    }
  },
  "timing": {
    "totalMs": 450,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 300
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 150
      }
    ]
  },
  "notes": [
    {
      "code": "ERROR_MANIFEST_INVALID",
      "message": "Manifest.json is missing required fields",
      "details": {
        "missingFields": ["compose.photos"],
        "manifestPath": "app/data/_templates/tpl_001/0.1.0/abc123.../manifest.json"
      }
    }
  ]
}
```

### 资源文件缺失

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "MANIFEST_VALIDATION_ERROR",
    "message": "Required asset file not found",
    "detail": {
      "reason": "Background image file does not exist",
      "expectedPath": "app/data/_templates/tpl_001/0.1.0/abc123.../assets/bg.png",
      "templateCode": "tpl_001"
    }
  },
  "timing": {
    "totalMs": 380,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 250
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 130
      }
    ]
  },
  "notes": [
    {
      "code": "ERROR_ASSET_MISSING",
      "message": "Background image file is missing from template package",
      "details": {
        "assetType": "background",
        "expectedPath": "assets/bg.png"
      }
    }
  ]
}
```

### 渲染失败

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "RENDER_ERROR",
    "message": "Failed to render final image",
    "detail": {
      "reason": "Raw image file not found",
      "rawPath": "D:/path/to/nonexistent/image.jpg"
    }
  },
  "timing": {
    "totalMs": 1200,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 300
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 15
      },
      {
        "name": "RENDER",
        "ms": 885
      }
    ]
  },
  "notes": [
    {
      "code": "ERROR_RENDER_FAILED",
      "message": "Image rendering failed due to missing input file",
      "details": {
        "stage": "RENDER",
        "errorType": "FileNotFoundError"
      }
    }
  ]
}
```

### 存储失败

```json
{
  "ok": false,
  "jobId": "job_20240101_123456_abc123",
  "error": {
    "code": "STORE_ERROR",
    "message": "Failed to store rendered image",
    "detail": {
      "reason": "Disk space insufficient",
      "targetPath": "D:\\AICreama\\booth\\data\\final\\job_20240101_123456_abc123\\final.png",
      "availableSpace": 1024
    }
  },
  "timing": {
    "totalMs": 2100,
    "steps": [
      {
        "name": "TEMPLATE_RESOLVE",
        "ms": 400
      },
      {
        "name": "MANIFEST_LOAD",
        "ms": 20
      },
      {
        "name": "RENDER",
        "ms": 1500
      },
      {
        "name": "STORE",
        "ms": 180
      }
    ]
  },
  "notes": [
    {
      "code": "ERROR_STORAGE_FAILED",
      "message": "Failed to write final image to disk",
      "details": {
        "error": "OSError: [Errno 28] No space left on device",
        "targetPath": "D:\\AICreama\\booth\\data\\final\\job_20240101_123456_abc123\\final.png"
      }
    }
  ]
}
```

### 请求参数错误（无 jobId）

```json
{
  "ok": false,
  "jobId": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid request parameters",
    "detail": {
      "reason": "Missing required field: templateCode",
      "missingFields": ["templateCode"]
    }
  },
  "timing": null,
  "notes": [
    {
      "code": "ERROR_INVALID_REQUEST",
      "message": "Request validation failed",
      "details": {
        "validationErrors": [
          {
            "field": "templateCode",
            "message": "Field required"
          }
        ]
      }
    }
  ]
}
```

---

## Notes 字段说明

`notes` 字段是一个数组，包含处理过程中的提示信息。每个 note 包含：

- **code**: 提示代码，用于程序化处理（如 `TEMPLATE_CACHED`, `WARN_LOW_QUALITY`）
- **message**: 人类可读的提示消息
- **details**: 可选的额外详情字典，包含更具体的信息

### Notes 代码示例

| Code | 说明 | 类型 |
|------|------|------|
| `TEMPLATE_CACHED` | 模板从缓存加载 | INFO |
| `TEMPLATE_DOWNLOADED` | 模板已下载 | INFO |
| `INFO_IMAGE_RESIZED` | 图像已调整大小 | INFO |
| `WARN_CHECKSUM_MISSING` | 校验和未提供 | WARNING |
| `WARN_LOW_QUALITY` | 图像质量较低 | WARNING |
| `ERROR_TEMPLATE_DOWNLOAD` | 模板下载失败 | ERROR |
| `ERROR_CHECKSUM_MISMATCH` | 校验和不匹配 | ERROR |
| `ERROR_MANIFEST_INVALID` | Manifest 无效 | ERROR |
| `ERROR_ASSET_MISSING` | 资源文件缺失 | ERROR |
| `ERROR_RENDER_FAILED` | 渲染失败 | ERROR |
| `ERROR_STORAGE_FAILED` | 存储失败 | ERROR |

---

## 字段说明

### 成功响应字段

- **ok**: `true`（字面量，固定为 true）
- **jobId**: 任务 ID，用于追踪和日志
- **template**: 使用的模板信息
  - `templateCode`: 模板代码
  - `versionSemver`: 版本号
  - `manifestVersion`: Manifest 版本
- **outputs**: 输出文件 URL
  - `previewUrl`: 预览图 URL（可选）
  - `finalUrl`: 最终图 URL（必需）
- **timing**: 处理时间信息
  - `totalMs`: 总处理时间（毫秒）
  - `steps`: 各步骤耗时列表
- **warnings**: 警告消息列表（字符串数组）
- **notes**: 提示信息列表（NoteItem 数组）

### 失败响应字段

- **ok**: `false`（字面量，固定为 false）
- **jobId**: 任务 ID（如果已生成，否则为 null）
- **error**: 错误信息字典
  - `code`: 错误代码
  - `message`: 错误消息
  - `detail`: 错误详情（可选）
- **timing**: 处理时间信息（如果已开始处理，否则为 null）
- **notes**: 提示信息列表（NoteItem 数组）

---

## 使用建议

1. **检查 `ok` 字段**：首先检查 `ok` 字段判断成功或失败
2. **处理错误**：如果 `ok` 为 `false`，检查 `error.code` 和 `error.message`
3. **查看提示**：检查 `notes` 字段了解处理过程中的额外信息
4. **性能监控**：使用 `timing` 字段监控各步骤性能
5. **警告处理**：检查 `warnings` 字段了解需要注意的问题
