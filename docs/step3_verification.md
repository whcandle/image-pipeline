# 步骤 3 验证：main.py 路由注册

## ✅ 已完成的工作

### 1. 路由导入（main.py 第 9 行）
```python
from app.routers.process import router as process_router
```
✅ **正确**：已导入 process_router

### 2. 路由注册（main.py 第 51 行）
```python
app.include_router(process_router)
```
✅ **正确**：已注册 process_router

### 3. 路由结构（app/routers/process.py）
```python
# v1 路由
router_v1 = APIRouter(prefix="/pipeline/v1", tags=["process"])

# v2 路由
router_v2 = APIRouter(prefix="/pipeline/v2", tags=["process_v2"])

# 统一导出
router = APIRouter()
router.include_router(router_v1)
router.include_router(router_v2)
```
✅ **正确**：process_router 包含 v1 和 v2 两个路由

---

## 📋 路由注册流程

```
main.py
  ↓
导入 process_router (第 9 行)
  ↓
注册 process_router (第 51 行)
  ↓
process_router 包含:
  ├── router_v1 → /pipeline/v1/process
  └── router_v2 → /pipeline/v2/process
```

---

## 🧪 验证方法

### 方法 1：启动服务并查看路由列表

1. **启动服务**：
   ```powershell
   cd D:\workspace\image-pipeline
   python -m uvicorn app.main:app --reload --port 9002
   ```

2. **访问 FastAPI 文档**：
   打开浏览器访问：`http://localhost:9002/docs`
   
   你应该能看到：
   - `/pipeline/v1/process` (POST)
   - `/pipeline/v2/process` (POST)

### 方法 2：使用 curl 测试路由

```powershell
# 测试 v2 路由
curl -X POST "http://localhost:9002/pipeline/v2/process" ^
  -H "Content-Type: application/json" ^
  -d "{\"templateCode\":\"tpl_001\",\"versionSemver\":\"0.1.1\",\"downloadUrl\":\"http://127.0.0.1:9000/tpl_001_v0.1.1.zip\",\"checksumSha256\":\"f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d\",\"rawPath\":\"D:/AICreama/imagePipeLineTmp/test.jpg\"}"

# 预期响应：
# {"finalUrl":"/files/v2/placeholder.png"}
```

### 方法 3：运行自动化测试

```powershell
cd D:\workspace\image-pipeline
pytest tests/test_process_api_v2.py -v
```

---

## ✅ 验证清单

- [x] `main.py` 中导入了 `process_router`
- [x] `main.py` 中注册了 `process_router`
- [x] `process.py` 中定义了 `router_v1` 和 `router_v2`
- [x] `process.py` 中统一导出了 `router`
- [x] v2 路由能正常响应请求（已验证：返回 `{"finalUrl":"/files/v2/placeholder.png"}`）

---

## 📝 总结

**步骤 3 已完成** ✅

- ✅ 路由已正确导入
- ✅ 路由已正确注册
- ✅ v1 和 v2 路由都能正常工作
- ✅ 服务可以正常启动

**下一步**：可以继续实现服务模块的具体功能（TemplateResolver、ManifestLoader、RenderEngine、StorageManager）
