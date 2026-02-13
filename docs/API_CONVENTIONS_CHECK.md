# 接口约定检查报告

## 检查时间
2024-XX-XX

## 约定要求

根据要求，以下接口和路径必须定死不改：

1. ✅ Pipeline 内部接口：`POST /pipeline/v2/process`
2. ✅ Pipeline 静态文件：`/files/preview/**`、`/files/final/**`
3. ❌ Gateway 对外接口：`POST /ai/v2/process` **待实现**
4. ❌ Gateway 对外文件：`/files/**`（代理到 pipeline）**待实现**

---

## 检查结果

### 1. Pipeline 内部接口 ✅

**要求**: `POST /pipeline/v2/process`

**实现状态**: ✅ **已完成**

**检查项**:
- [x] 路由定义存在: `app/routers/process.py:33-36`
- [x] 路由前缀正确: `/pipeline/v2`
- [x] 路由路径正确: `/process`
- [x] 完整路径: `POST /pipeline/v2/process` ✅

**代码位置**:
```python
# app/routers/process.py:33-36
router_v2 = APIRouter(prefix="/pipeline/v2", tags=["process_v2"])

@router_v2.post("/process")
async def process_v2(req: PipelineV2Request):
    ...
```

---

### 2. Pipeline 静态文件 ✅

**要求**: `/files/preview/**`、`/files/final/**`

**实现状态**: ✅ **已完成**

**检查项**:

#### 2.1 `/files/preview/**`
- [x] 静态文件挂载存在: `app/main.py:63-67`
- [x] 挂载路径正确: `/files/preview`
- [x] 物理路径正确: `{BOOTH_DATA_DIR}/preview/`
- [x] 目录自动创建: `app/main.py:59`

**代码位置**:
```python
# app/main.py:63-67
app.mount(
    "/files/preview",
    StaticFiles(directory=str(booth_root / "preview")),
    name="files_preview",
)
```

#### 2.2 `/files/final/**`
- [x] 静态文件挂载存在: `app/main.py:68-72`
- [x] 挂载路径正确: `/files/final`
- [x] 物理路径正确: `{BOOTH_DATA_DIR}/final/`
- [x] 目录自动创建: `app/main.py:60`

**代码位置**:
```python
# app/main.py:68-72
app.mount(
    "/files/final",
    StaticFiles(directory=str(booth_root / "final")),
    name="files_final",
)
```

---

### 3. Gateway 对外接口 ❌

**要求**: `POST /ai/v2/process`

**实现状态**: ❌ **未实现**

**当前状态**:
- 只有 `/ai/v1/process` 路由（`ai-gateway/src/main/java/com/mg/aigateway/api/AiController.java:12`）
- 缺少 `/ai/v2/process` 路由

**需要实现**:
1. 在 `AiController` 中添加 `/ai/v2` 路由前缀
2. 创建 `POST /ai/v2/process` 方法
3. 代理请求到 `http://pipeline:9002/pipeline/v2/process`

**建议实现**:
```java
@RestController
@RequestMapping("/ai/v2")
public class AiV2Controller {
    
    @PostMapping("/process")
    public AiProcessResponse processV2(
        @RequestHeader(name = "X-Device-Id") String deviceId,
        @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody AiProcessV2Request req
    ) {
        // 代理到 pipeline /pipeline/v2/process
        return gateway.processV2(deviceId, idempotencyKey, req);
    }
}
```

---

### 4. Gateway 文件代理 ❌

**要求**: `/files/**`（代理到 pipeline）

**实现状态**: ❌ **未实现**

**当前状态**:
- 未实现文件代理功能
- 客户端无法通过 Gateway 访问 Pipeline 的静态文件

**需要实现**:
1. 配置 Spring Cloud Gateway 或 WebClient 代理
2. 代理规则: `GET /files/**` → `GET http://pipeline:9002/files/**`
3. 确保所有 `/files/**` 请求都转发到 Pipeline

**建议实现**:
```java
@Configuration
public class FileProxyConfig {
    
    @Bean
    public RouterFunction<ServerResponse> fileProxyRoute() {
        return RouterFunctions.route(
            RequestPredicates.path("/files/**"),
            request -> {
                String path = request.path().substring("/files".length());
                String pipelineUrl = "http://localhost:9002/files" + path;
                // 使用 WebClient 转发请求
                return webClient.get()
                    .uri(pipelineUrl)
                    .retrieve()
                    .bodyToMono(ServerResponse.class);
            }
        );
    }
}
```

---

## 总结

### 已完成 ✅

1. ✅ Pipeline 内部接口: `POST /pipeline/v2/process`
2. ✅ Pipeline 静态文件: `/files/preview/**`、`/files/final/**`

### 待完成 ❌

1. ❌ Gateway 对外接口: `POST /ai/v2/process`
2. ❌ Gateway 文件代理: `/files/**` → Pipeline

---

## 下一步行动

### Gateway 开发任务

1. **实现 `/ai/v2/process` 接口**
   - 创建 `AiV2Controller` 或扩展 `AiController`
   - 添加 `POST /ai/v2/process` 路由
   - 实现请求代理到 Pipeline

2. **实现文件代理**
   - 配置 Spring Cloud Gateway 或使用 WebClient
   - 实现 `/files/**` 到 Pipeline 的代理
   - 确保 URL 转换正确（Gateway URL → Pipeline URL）

3. **更新文档**
   - 在 Gateway 的 README 中说明接口约定
   - 添加 API 文档

---

## 文档位置

- Pipeline 接口约定: `image-pipeline/docs/API_CONVENTIONS.md`
- Gateway 待实现: `ai-gateway/` (需要添加相应文档)

---

## 验证方法

### Pipeline 验证 ✅

```bash
# 测试处理接口
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{"templateCode": "tpl_001", ...}'

# 测试静态文件
curl http://localhost:9002/files/final/job_001/final.png
```

### Gateway 验证 ❌ (待实现后)

```bash
# 测试处理接口
curl -X POST http://localhost:8081/ai/v2/process \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: kiosk-001" \
  -d '{"templateCode": "tpl_001", ...}'

# 测试文件代理
curl http://localhost:8081/files/final/job_001/final.png
```
