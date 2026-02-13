# API 接口与路径约定（定死不改）

本文档定义了 pipeline 和 gateway 之间的接口与路径约定，**所有开发必须严格按照此约定执行**。

---

## 1. Pipeline 内部接口

### 1.1 处理接口

**路径**: `POST /pipeline/v2/process`

**说明**: Pipeline 服务内部的处理接口，用于接收模板驱动的图像处理请求。

**实现状态**: ✅ 已实现
- 路由定义: `app/routers/process.py:36`
- 路由前缀: `/pipeline/v2`
- 完整路径: `/pipeline/v2/process`

**请求体**:
```json
{
  "templateCode": "tpl_001",
  "versionSemver": "0.1.0",
  "downloadUrl": "http://example.com/template.zip",
  "checksumSha256": "abc123...",
  "rawPath": "D:/path/to/raw/image.jpg"
}
```

**响应**:
```json
{
  "finalUrl": "http://localhost:9002/files/final/job_001/final.png",
  "previewUrl": "http://localhost:9002/files/preview/job_001/preview.png"
}
```

---

## 2. Pipeline 静态文件服务

### 2.1 预览图服务

**路径**: `/files/preview/**`

**说明**: 提供预览图的静态文件服务。

**实现状态**: ✅ 已实现
- 挂载点: `app/main.py:63-67`
- 物理路径: `{BOOTH_DATA_DIR}/preview/`
- 示例 URL: `http://localhost:9002/files/preview/job_001/preview.png`

### 2.2 最终图服务

**路径**: `/files/final/**`

**说明**: 提供最终合成图的静态文件服务。

**实现状态**: ✅ 已实现
- 挂载点: `app/main.py:68-72`
- 物理路径: `{BOOTH_DATA_DIR}/final/`
- 示例 URL: `http://localhost:9002/files/final/job_001/final.png`

### 2.3 兼容性说明

**路径**: `/files/**` (旧版兼容)

**说明**: 旧版接口的静态文件服务，保持向后兼容。

**实现状态**: ✅ 已实现
- 挂载点: `app/main.py:75`
- 物理路径: `{PIPELINE_DATA_DIR}/`

---

## 3. Gateway 对外接口

### 3.1 处理接口

**路径**: `POST /ai/v2/process`

**说明**: Gateway 对外提供的图像处理接口，客户端应调用此接口。

**实现状态**: ❌ **待实现**
- 当前状态: 只有 `/ai/v1/process` (见 `ai-gateway/src/main/java/com/mg/aigateway/api/AiController.java:12`)
- 需要添加: `/ai/v2/process` 路由，代理到 pipeline 的 `/pipeline/v2/process`

**请求头**:
```
X-Device-Id: kiosk-001
Idempotency-Key: sess_001#0#tpl_001 (可选)
```

**请求体**: 同 Pipeline V2 接口

**响应**: 同 Pipeline V2 接口（可能包含额外的 gateway 元数据）

---

## 4. Gateway 文件代理

### 4.1 文件代理服务

**路径**: `/files/**`

**说明**: Gateway 代理所有 `/files/**` 请求到 Pipeline 服务。

**实现状态**: ❌ **待实现**
- 当前状态: 未实现文件代理
- 需要实现: Spring Cloud Gateway 或 WebClient 代理 `/files/**` 到 `http://localhost:9002/files/**`

**代理规则**:
- Gateway 接收: `http://gateway:8081/files/preview/job_001/preview.png`
- 转发到: `http://pipeline:9002/files/preview/job_001/preview.png`
- 返回: Pipeline 的响应（文件内容）

---

## 5. 完整请求流程

### 5.1 客户端 → Gateway → Pipeline

```
1. 客户端调用: POST http://gateway:8081/ai/v2/process
   ↓
2. Gateway 转发: POST http://pipeline:9002/pipeline/v2/process
   ↓
3. Pipeline 处理:
   - TemplateResolver: 下载并解析模板
   - ManifestLoader: 加载 manifest.json
   - RenderEngine: 渲染合成图像
   - StorageManager: 保存图像到 {BOOTH_DATA_DIR}/preview|final/{jobId}/
   ↓
4. Pipeline 返回: { "finalUrl": "http://pipeline:9002/files/final/job_001/final.png" }
   ↓
5. Gateway 返回: { "finalUrl": "http://gateway:8081/files/final/job_001/final.png" }
   ↓
6. 客户端访问: GET http://gateway:8081/files/final/job_001/final.png
   ↓
7. Gateway 代理: GET http://pipeline:9002/files/final/job_001/final.png
   ↓
8. Pipeline 返回: 文件内容
```

---

## 6. 实现检查清单

### Pipeline 服务 (image-pipeline)

- [x] ✅ `POST /pipeline/v2/process` 路由已实现
- [x] ✅ `/files/preview/**` 静态文件挂载已实现
- [x] ✅ `/files/final/**` 静态文件挂载已实现
- [x] ✅ `/files/**` 兼容性挂载已实现

### Gateway 服务 (ai-gateway)

- [ ] ❌ `POST /ai/v2/process` 路由**待实现**
- [ ] ❌ `/files/**` 文件代理**待实现**

---

## 7. 开发规范

### 7.1 路径约定

- **Pipeline 内部接口**: 必须以 `/pipeline/v2/` 开头
- **Gateway 对外接口**: 必须以 `/ai/v2/` 开头
- **静态文件路径**: 统一使用 `/files/` 前缀

### 7.2 URL 生成规范

**Pipeline 内部生成 URL**:
```python
# 使用 pipeline 的 PUBLIC_BASE_URL
url = f"{settings.PUBLIC_BASE_URL}/files/final/{job_id}/final.png"
# 示例: http://localhost:9002/files/final/job_001/final.png
```

**Gateway 返回给客户端**:
```java
// Gateway 需要将 pipeline 的 URL 转换为 gateway 的 URL
String pipelineUrl = "http://localhost:9002/files/final/job_001/final.png";
String gatewayUrl = pipelineUrl.replace("http://localhost:9002", "http://gateway:8081");
// 结果: http://gateway:8081/files/final/job_001/final.png
```

### 7.3 错误处理

- Pipeline 返回的错误应包含明确的错误码和消息
- Gateway 应保持错误信息的完整性，不丢失 Pipeline 的错误详情

---

## 8. 测试验证

### 8.1 Pipeline 测试

```bash
# 测试处理接口
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "downloadUrl": "http://example.com/template.zip",
    "rawPath": "D:/path/to/image.jpg"
  }'

# 测试静态文件服务
curl http://localhost:9002/files/final/job_001/final.png
```

### 8.2 Gateway 测试（待实现后）

```bash
# 测试处理接口
curl -X POST http://localhost:8081/ai/v2/process \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: kiosk-001" \
  -d '{
    "templateCode": "tpl_001",
    "versionSemver": "0.1.0",
    "downloadUrl": "http://example.com/template.zip",
    "rawPath": "D:/path/to/image.jpg"
  }'

# 测试文件代理
curl http://localhost:8081/files/final/job_001/final.png
```

---

## 9. 更新日志

- **2024-XX-XX**: 创建接口约定文档
- **2024-XX-XX**: Pipeline V2 接口和静态文件服务已实现
- **2024-XX-XX**: Gateway V2 接口和文件代理待实现

---

## 10. 注意事项

1. **路径约定不可更改**: 所有路径约定已定死，不得随意修改
2. **向后兼容**: 保持 `/pipeline/v1/process` 和 `/files/**` 的兼容性
3. **URL 转换**: Gateway 必须将 Pipeline 的 URL 转换为 Gateway 的 URL
4. **文件代理**: Gateway 必须实现文件代理，确保客户端可以通过 Gateway 访问文件
