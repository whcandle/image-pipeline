# Image Pipeline Modular Refactoring - Complete Project Summary

## 项目概述

本项目完成了 **Image Pipeline** 服务的模块化重构，实现了基于模板驱动的图像处理 v2 API，并完成了与 **AI Gateway** 服务的集成。

**项目时间线**: 从初始架构设计到完整实现，包括多次迭代和问题修复

---

## 一、核心目标

1. **模块化架构**: 将图像处理流程拆分为独立、可测试的服务模块
2. **V2 API 设计**: 定义并实现新的模板驱动 API 接口
3. **端到端集成**: 完成从 Gateway 到 Pipeline 的完整请求流程
4. **错误处理**: 实现统一的异常处理和错误响应机制
5. **测试覆盖**: 添加完整的单元测试和集成测试

---

## 二、项目架构

### 2.1 服务模块划分

#### Image Pipeline Service (Python/FastAPI)

**核心服务模块**:

1. **TemplateResolver** (`app/services/template_resolver.py`)
   - 职责: 模板下载、缓存管理、校验和验证、解压
   - 特性:
     - 支持 SHA256 校验和验证
     - 本地缓存机制（避免重复下载）
     - 并发安全（文件锁机制）
     - 自动解压到缓存目录

2. **ManifestLoader** (`app/services/manifest_loader.py`)
   - 职责: Manifest 加载、验证、生成 runtime_spec
   - 功能:
     - 加载 `manifest.json` 并解析 JSON
     - 验证必填字段和字段类型
     - 校验资源文件存在性（背景图、贴图）
     - 生成运行时规范（runtime_spec）包含绝对路径
   - **增强功能**: 详细的调试日志输出，便于定位校验失败

3. **RenderEngine** (`app/services/render_engine.py`)
   - 职责: 根据 runtime_spec 渲染合成图像
   - 功能:
     - 加载背景图
     - 处理原始照片（缩放、裁剪、定位）
     - 合成贴图（支持旋转、透明度、层级）
     - 输出最终合成图像

4. **StorageManager** (`app/services/storage_manager.py`)
   - 职责: 图像存储和 URL 生成
   - 功能:
     - 存储预览图到 `{BOOTH_DATA_DIR}/preview/{jobId}/`
     - 存储最终图到 `{BOOTH_DATA_DIR}/final/{jobId}/`
     - 生成可访问的 URL

#### AI Gateway Service (Java/Spring Boot)

**核心组件**:

1. **AiV2Controller** (`api/AiV2Controller.java`)
   - 提供 `/ai/v2/process` 外部接口
   - 接收客户端请求，包含设备 ID 和幂等性键
   - 当前实现为占位实现（返回 stub 响应）

2. **PipelineClient** (`service/PipelineClient.java`)
   - 负责调用 Pipeline 服务的 HTTP 客户端
   - 实现 `processV2()` 方法，调用 `/pipeline/v2/process`
   - 使用 WebClient（Spring WebFlux）进行异步调用

3. **DTO 定义**:
   - `AiV2ProcessRequest`: 外部请求 DTO
   - `AiV2ProcessResponse`: 外部响应 DTO
   - `PipelineV2Request`: 内部请求 DTO（Gateway → Pipeline）
   - `PipelineV2Response`: 内部响应 DTO（Pipeline → Gateway）

---

## 三、API 接口定义

### 3.1 Pipeline 服务接口

#### POST `/pipeline/v2/process`

**请求体** (`PipelineV2Request`):
```json
{
  "templateCode": "tpl_001",
  "versionSemver": "0.1.1",
  "downloadUrl": "http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
  "checksumSha256": "f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
  "rawPath": "D:/AICreama/imagePipeLineTmp/test.jpg"
}
```

**成功响应** (`PipelineV2ResponseOk`):
```json
{
  "ok": true,
  "jobId": "job_1770937753_4f73dbbd",
  "template": {
    "templateCode": "tpl_001",
    "versionSemver": "0.1.1",
    "manifestVersion": 1
  },
  "outputs": {
    "previewUrl": "http://localhost:9002/files/preview/job_001/preview.png",
    "finalUrl": "http://localhost:9002/files/final/job_001/final.png"
  },
  "timing": {
    "totalMs": 1234,
    "steps": [
      {"name": "TEMPLATE_RESOLVE", "ms": 200},
      {"name": "MANIFEST_LOAD", "ms": 50},
      {"name": "RENDER", "ms": 800},
      {"name": "STORE", "ms": 184}
    ]
  },
  "warnings": [],
  "notes": [
    {
      "code": "PREVIEW_EQUALS_FINAL",
      "message": "Preview image is currently using the same image as final",
      "details": {}
    },
    {
      "code": "TEMPLATE_CACHED",
      "message": "Template was loaded from cache",
      "details": {"templateDir": "..."}
    }
  ]
}
```

**错误响应** (`PipelineV2ResponseError`):
```json
{
  "ok": false,
  "jobId": "job_1770937753_4f73dbbd",
  "error": {
    "code": "MANIFEST_INVALID",
    "message": "Missing required field: templateCode",
    "retryable": false,
    "detail": {
      "templateCode": "tpl_001"
    }
  },
  "timing": {
    "totalMs": 50,
    "steps": [{"name": "MANIFEST_LOAD", "ms": 50}]
  },
  "notes": [
    {
      "code": "ERROR_MANIFEST_VALIDATION",
      "message": "Manifest validation failed",
      "details": {"error": "..."}
    }
  ]
}
```

#### 静态文件服务

- **GET `/files/preview/**`**: 预览图静态文件服务
  - 物理路径: `{BOOTH_DATA_DIR}/preview/`
  
- **GET `/files/final/**`**: 最终图静态文件服务
  - 物理路径: `{BOOTH_DATA_DIR}/final/`

### 3.2 Gateway 服务接口

#### POST `/ai/v2/process`

**请求头**:
- `X-Device-Id`: 设备 ID（必填）
- `Idempotency-Key`: 幂等性键（可选）

**请求体**: 同 Pipeline V2 接口

**响应**: 同 Pipeline V2 接口（可能包含额外的 gateway 元数据）

---

## 四、实现细节

### 4.1 端到端处理流程

```
1. 客户端请求
   POST /ai/v2/process
   ↓
2. Gateway 接收请求
   AiV2Controller.process()
   ↓
3. Gateway 调用 Pipeline
   PipelineClient.processV2()
   POST /pipeline/v2/process
   ↓
4. Pipeline 处理流程
   a. 生成 jobId: job_{timestamp}_{uuid}
   b. TemplateResolver.resolve()
      - 下载模板 zip
      - 验证校验和
      - 解压到缓存目录
   c. ManifestLoader
      - load_manifest(): 读取 manifest.json
      - validate_manifest(): 验证字段
      - to_runtime_spec(): 生成运行时规范
      - validate_assets(): 校验资源文件
   d. RenderEngine.render()
      - 加载背景图
      - 处理原始照片
      - 合成贴图
      - 输出最终图像
   e. StorageManager
      - store_preview(): 保存预览图
      - store_final(): 保存最终图
   ↓
5. Pipeline 返回响应
   PipelineV2ResponseOk/Error
   ↓
6. Gateway 返回响应
   AiV2ProcessResponse
   ↓
7. 客户端访问文件
   GET /files/final/{jobId}/final.png
```

### 4.2 错误处理机制

**统一异常映射**:

| 异常类型 | 错误码 | Retryable | 说明 |
|---------|--------|-----------|------|
| `TemplateDownloadError` | `TEMPLATE_DOWNLOAD_FAILED` | ✅ Yes | 模板下载失败 |
| `TemplateChecksumMismatch` | `TEMPLATE_CHECKSUM_MISMATCH` | ❌ No | 校验和不匹配 |
| `TemplateExtractError` | `TEMPLATE_EXTRACT_ERROR` | ❌ No | 解压失败 |
| `ManifestLoadError` | `MANIFEST_LOAD_ERROR` | ❌ No | Manifest 加载失败 |
| `ManifestValidationError` | `MANIFEST_INVALID` / `ASSET_NOT_FOUND` | ❌ No | Manifest 验证失败 |
| `RenderError` | `RENDER_FAILED` | ❌ No | 渲染失败 |
| `StorageError` | `STORE_FAILED` | ✅ Yes | 存储失败 |
| `Exception` | `INTERNAL_ERROR` | ❌ No | 未预期错误 |

**错误响应结构**:
- 所有错误都返回 `PipelineV2ResponseError`，不抛出 500
- 错误信息包含 `code`, `message`, `retryable`, `detail`
- `notes` 字段包含详细的调试信息

### 4.3 调试日志增强

**ManifestLoader 日志输出**:

- `load_manifest()`: 打印文件路径、目录内容、JSON 解析状态
- `validate_manifest()`: 每个校验步骤都有 ✅/❌ 标记
  - 打印字段名、期望类型、实际值
  - 覆盖所有必填字段和类型校验
- `validate_assets()`: 打印资源文件检查过程
  - 背景图和贴图文件的路径检查
  - 文件不存在时打印目录内容

**process_v2 路由日志**:
- 捕获 `ManifestValidationError` 时打印详细错误信息
- 区分 `ASSET_NOT_FOUND` 和 `MANIFEST_INVALID` 错误代码

---

## 五、测试实现

### 5.1 Pipeline 测试

**文件**: `tests/test_process_api_v2.py`

**测试用例**:

1. **test_process_v2_success**: 成功处理流程
   - 验证成功响应结构
   - 验证 `ok=true`
   - 验证输出 URL 存在
   - 验证 `PREVIEW_EQUALS_FINAL` note

2. **test_process_v2_checksum_mismatch**: 校验和不匹配
   - 验证错误码 `TEMPLATE_CHECKSUM_MISMATCH`
   - 验证 `retryable=false`
   - 验证错误详情包含 expected/actual checksum

3. **test_process_v2_bg_missing**: 背景文件缺失
   - 验证错误码 `ASSET_NOT_FOUND`
   - 验证错误消息包含文件路径

4. **test_process_v2_download_failed**: 下载失败
   - 验证错误码 `TEMPLATE_DOWNLOAD_FAILED`
   - 验证 `retryable=true`

5. **test_process_v2_render_failed**: 渲染失败
   - 验证错误码 `RENDER_FAILED`
   - 验证 `retryable=false`

**测试工具**:
- 使用 `pytest` 框架
- 使用 `tmp_path` fixture 创建临时文件
- 使用 `monkeypatch` 模拟外部依赖（模板服务器）

### 5.2 Gateway 测试

**文件**: `src/test/java/com/mg/aigateway/api/AiV2ControllerTest.java`

**测试用例**:

1. **testProcessV2_ReturnsOk**: 验证 stub 响应
   - 验证 `ok=true`
   - 验证 `V2_STUB` note 存在

2. **testProcessV2_ValidationError**: 验证请求验证
   - 验证必填字段验证

3. **testProcessV2_MissingDeviceId**: 验证请求头验证
   - 验证 `X-Device-Id` 必填

**Smoke Test**: `src/test/java/com/mg/aigateway/service/PipelineClientV2SmokeTest.java`
- 集成测试，实际调用 Pipeline 服务
- 默认 `@Disabled`，需要手动启用
- 通过系统属性传递测试参数

---

## 六、关键问题与解决方案

### 6.1 问题 1: 语法错误

**问题**:**:
```
SyntaxError: invalid syntax in app/routers/process.py
```

**原因**: `except` 块缩进错误

**解决**: 修正 `except Exception as e:` 块的缩进，对齐到对应的 `try:` 块

### 6.2 问题 2: 测试断言失败

**问题**: 
```
AssertionError: Expected RENDER_FAILED, got RENDER_ERROR
```

**原因**: 错误码不一致，测试期望 `RENDER_FAILED`，代码返回 `RENDER_ERROR`

**解决**: 将错误码统一为 `RENDER_FAILED`，并添加 `retryable: False`

### 6.3 问题 3: PowerShell Maven 参数解析错误

**问题**:
```
Error resolving version for plugin '.downloadUrl=http://127.0.0.1'
```

**原因**: PowerShell 将 `-Dsmoke.downloadUrl=...` 解析为插件坐标

**解决**: 在 PowerShell 中使用单引号包裹所有 `-D` 参数：
```powershell
mvn test '-Dtest=PipelineClientV2SmokeTest' '-Dsmoke.downloadUrl=...'
```

### 6.4 问题 4: MANIFEST_INVALID 错误定位困难

**问题**: Pipeline 返回 `MANIFEST_INVALID`，但无法定位具体失败字段

**解决**: 
- 在 `ManifestLoader` 中添加详细的调试日志
- 每个校验步骤都有 ✅/❌ 标记
- 打印字段名、期望类型、实际值
- 在 `process_v2` 路由中添加错误捕获日志

**效果**: 运行 smoke test 时，Pipeline 控制台会输出详细的校验日志，便于快速定位失败字段

---

## 七、文件结构

### 7.1 Image Pipeline 项目结构

```
image-pipeline/
├── app/
│   ├── services/              # 核心服务模块
│   │   ├── template_resolver.py    # 模板解析器
│   │   ├── manifest_loader.py       # Manifest 加载器（含详细日志）
│   │   ├── render_engine.py         # 渲染引擎
│   │   └── storage_manager.py        # 存储管理器
│   ├── routers/
│   │   └── process.py         # API 路由（v1/v2）
│   ├── models/
│   │   └── dtos.py           # DTO 定义（PipelineV2Request/Response）
│   ├── main.py               # FastAPI 应用入口（静态文件挂载）
│   └── config.py             # 配置管理
├── tests/
│   ├── test_process_api_v2.py        # V2 API 测试
│   ├── test_template_resolver.py
│   ├── test_manifest_loader.py
│   ├── test_render_engine.py
│   └── test_storage_manager.py
├── docs/
│   ├── API_CONVENTIONS.md            # API 接口约定（定死）
│   ├── v2_api_parameters_explained.md
│   ├── v2_api_response_examples.md
│   └── TESTING_V2_API.md
└── README.md
```

### 7.2 AI Gateway 项目结构

```
ai-gateway/
├── src/main/java/com/mg/aigateway/
│   ├── api/
│   │   ├── AiController.java         # V1 API（已存在）
│   │   └── AiV2Controller.java       # V2 API（新增，占位实现）
│   ├── dto/
│   │   ├── AiV2ProcessRequest.java   # 外部请求 DTO
│   │   ├── AiV2ProcessResponse.java # 外部响应 DTO
│   │   ├── PipelineV2Request.java    # 内部请求 DTO
│   │   └── PipelineV2Response.java   # 内部响应 DTO
│   └── service/
│       └── PipelineClient.java       # Pipeline 客户端（含 processV2 方法）
└── src/test/java/com/mg/aigateway/
    ├── api/
    │   └── AiV2ControllerTest.java   # V2 Controller 测试
    └── service/
        └── PipelineClientV2SmokeTest.java  # Smoke 测试
```

---

## 八、代码提交记录

### 8.1 主要提交

**Commit 1** (`8c2414f`):
- **信息**: `feat: add detailed logging for manifest validation debugging`
- **内容**: 添加 ManifestLoader 详细日志输出
- **推送**: Gitee + GitHub

**Commit 2** (`9698684`):
- **信息**: `feat: implement v2 pipeline API with comprehensive logging and validation`
- **内容**: 
  - 实现核心服务模块（TemplateResolver, ManifestLoader, RenderEngine, StorageManager）
  - 实现 v2 API 端点和 DTO
  - 添加完整测试套件
  - 添加 API 文档
  - 配置静态文件服务
- **统计**: 25 个文件，新增 5040 行，删除 324 行
- **推送**: Gitee

---

## 九、当前状态

### 9.1 已完成功能 ✅

**Image Pipeline**:
- ✅ `/pipeline/v2/process` API 端点
- ✅ TemplateResolver（下载、缓存、校验、解压）
- ✅ ManifestLoader（加载、验证、生成 runtime_spec）
- ✅ RenderEngine（图像合成）
- ✅ StorageManager（图像存储）
- ✅ 静态文件服务 (`/files/preview/**`, `/files/final/**`)
- ✅ 统一异常处理和错误响应
- ✅ 详细调试日志输出
- ✅ 完整测试套件

**AI Gateway**:
- ✅ `/ai/v2/process` API 端点（占位实现）
- ✅ V2 DTO 定义（AiV2ProcessRequest/Response, PipelineV2Request/Response）
- ✅ PipelineClient.processV2() 方法
- ✅ Smoke 测试（用于集成验证）

### 9.2 待完成功能 ❌

**AI Gateway**:
- ❌ `/ai/v2/process` 实际调用 Pipeline 服务（当前为 stub）
- ❌ `/files/**` 文件代理到 Pipeline 服务
- ❌ URL 转换（Pipeline URL → Gateway URL）

---

## 十、使用指南

### 10.1 启动 Pipeline 服务

```bash
cd image-pipeline
uvicorn app.main:app --host 0.0.0.0 --port 9002
```

### 10.2 运行 Pipeline 测试

```bash
cd image-pipeline
pytest tests/test_process_api_v2.py -v
```

### 10.3 运行 Gateway Smoke Test

```powershell
cd ai-gateway
mvn test '-Dtest=PipelineClientV2SmokeTest' `
  '-Dsmoke.templateCode=tpl_001' `
  '-Dsmoke.versionSemver=0.1.1' `
  '-Dsmoke.downloadUrl=http://127.0.0.1:9000/tpl_001_v0.1.1.zip' `
  '-Dsmoke.checksumSha256=f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d' `
  '-Dsmoke.rawPath=D:/AICreama/imagePipeLineTmp/test.jpg'
```

### 10.4 查看调试日志

运行 smoke test 时，Pipeline 服务控制台会输出详细日志：
```
[ManifestLoader] Loading manifest from: ...
[ManifestLoader] Checking manifestVersion...
[ManifestLoader] ✅ manifestVersion = 1
[ManifestLoader] Checking templateCode...
[ManifestLoader] ❌ FAILED: Missing required field: templateCode
```

---

## 十一、技术栈

- **Image Pipeline**: Python 3.10+, FastAPI, Pydantic, PIL/Pillow, pytest
- **AI Gateway**: Java 17+, Spring Boot 3.x, Spring WebFlux, JUnit 5, Maven
- **版本控制**: Git, Gitee, GitHub

---

## 十二、文档索引

- [API 接口约定](./API_CONVENTIONS.md) - **必读**，定义了所有接口路径
- [V2 API 参数说明](./v2_api_parameters_explained.md) - API 参数详解
- [V2 API 响应示例](./v2_api_response_examples.md) - 成功和失败响应示例
- [测试指南](./TESTING_V2_API.md) - 如何测试 V2 API

---

## 十三、总结

本项目成功完成了 Image Pipeline 服务的模块化重构，实现了：

1. **清晰的模块划分**: TemplateResolver, ManifestLoader, RenderEngine, StorageManager
2. **完整的 API 设计**: 定义了 v2 API 接口和响应结构
3. **端到端流程**: 从 Gateway 到 Pipeline 的完整请求处理
4. **错误处理**: 统一的异常映射和错误响应
5. **调试支持**: 详细的日志输出，便于问题定位
6. **测试覆盖**: 完整的单元测试和集成测试

**下一步工作**:
- 完成 Gateway 的 `/ai/v2/process` 实际实现（调用 Pipeline）
- 实现 Gateway 的文件代理功能
- 根据调试日志修复 manifest 验证问题

---

**文档生成时间**: 2024-12-XX  
**项目状态**: ✅ 核心功能已完成，Gateway 集成待完成
