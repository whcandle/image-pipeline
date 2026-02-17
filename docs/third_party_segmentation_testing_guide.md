# ThirdPartySegmentationProvider 测试指南

## 📋 功能概述

`ThirdPartySegmentationProvider` 用于调用第三方抠图 API（如 remove.bg），将图片转换为透明背景的 RGBA 格式。

**关键特性：**
- 支持多种输入格式（PIL Image、bytes、文件路径）
- 统一输出为 RGBA（透明 PNG）
- 支持 remove.bg API（multipart 上传）
- 完善的错误处理（HTTP 状态码、响应摘要）
- API key 认证（X-Api-Key header）

## 🧪 测试方法

### 方法 1: 运行 pytest 自动化测试（推荐）

```bash
cd D:\workspace\image-pipeline

# 运行所有 ThirdPartySegmentationProvider 测试
pytest tests/test_third_party_segmentation.py -v
```

**测试覆盖：**

1. ✅ `test_removebg_success`: remove.bg 成功调用
2. ✅ `test_removebg_api_key_error`: API key 错误处理
3. ✅ `test_removebg_timeout`: 超时处理
4. ✅ `test_removebg_missing_api_key`: 缺少 API key
5. ✅ `test_removebg_unsupported_provider`: 不支持的 provider
6. ✅ `test_input_image_pil`: 输入为 PIL Image
7. ✅ `test_input_image_bytes`: 输入为 bytes
8. ✅ `test_input_image_path`: 输入为文件路径

---

### 方法 2: 使用测试脚本（本地测试）

```bash
cd D:\workspace\image-pipeline

# 方式 1: 通过命令行参数传递 API key
python scripts/test_third_party_segmentation.py test.jpg your_api_key

# 方式 2: 通过环境变量传递 API key
set REMOVEBG_API_KEY=your_api_key
python scripts/test_third_party_segmentation.py test.jpg
```

**输出：**
- 成功：在 `test_output/` 目录生成 `cutout_<原文件名>.png`
- 失败：显示错误信息和状态码

---

### 方法 3: 通过测试 API endpoint（需要启动服务）

#### 步骤 1: 启用测试路由

设置环境变量：
```bash
set ENABLE_TEST_ROUTES=true
```

或在 `.env` 文件中：
```bash
ENABLE_TEST_ROUTES=true
```

#### 步骤 2: 启动服务

```bash
cd D:\workspace\image-pipeline
uvicorn app.main:app --reload --port 9002
```

#### 步骤 3: 调用测试 API

**使用 curl：**
```bash
curl -X POST http://localhost:9002/test/segmentation/removebg \
  -F "image=@test.jpg" \
  -F "api_key=your_api_key" \
  -F "timeout_ms=30000" \
  --output cutout_result.png
```

**使用 PowerShell：**
```powershell
$form = @{
    image = Get-Item -Path "test.jpg"
    api_key = "your_api_key"
    timeout_ms = 30000
}
Invoke-RestMethod -Uri "http://localhost:9002/test/segmentation/removebg" `
  -Method Post `
  -Form $form `
  -OutFile "cutout_result.png"
```

**使用 Python requests：**
```python
import requests

with open("test.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:9002/test/segmentation/removebg",
        files={"image": f},
        data={
            "api_key": "your_api_key",
            "timeout_ms": 30000,
        },
    )

if response.status_code == 200:
    with open("cutout_result.png", "wb") as out:
        out.write(response.content)
    print("✅ Success! Saved to cutout_result.png")
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.json())
```

---

## ✅ 验证清单

### 成功场景
- [x] 输入 JPG/PNG 图片
- [x] 返回透明背景的 PNG（RGBA 模式）
- [x] 输出图片尺寸与输入一致
- [x] 背景区域透明（alpha=0）

### 错误场景
- [x] API key 错误：返回 401，抛出 `SegmentationProviderError`
- [x] 超时：抛出 `SegmentationProviderError`，包含 timeout 信息
- [x] 网络错误：抛出 `SegmentationProviderError`，包含错误摘要
- [x] 缺少 API key：抛出 `SegmentationProviderError`，提示缺少 key

---

## 🔍 调试技巧

### 1. 检查输入图片格式

```python
from PIL import Image
img = Image.open("test.jpg")
print(f"Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
```

### 2. 检查输出图片

```python
result = Image.open("cutout_result.png")
print(f"Mode: {result.mode}")  # 应该是 RGBA
print(f"Has transparency: {result.mode == 'RGBA'}")
```

### 3. 查看错误详情

如果 API 调用失败，检查：
- HTTP 状态码（401=认证失败，429=限流，500=服务器错误）
- 响应摘要（在异常中）

---

## 📝 API 使用示例

### remove.bg API 规范

**请求：**
- Method: POST
- Content-Type: multipart/form-data
- Header: `X-Api-Key: <api_key>`
- Field: `image_file` (文件)
- Optional: `size` (auto/preview/regular/hd/4k)
- Optional: `format` (auto/png/jpg)

**响应：**
- 成功 (200): PNG bytes (RGBA)
- 失败 (401/429/500): JSON 错误信息

---

## 🚨 常见问题

### Q: API key 在哪里获取？

**A:** 从 remove.bg 官网注册账号并获取 API key：https://www.remove.bg/api

### Q: 如何验证输出是透明的？

**A:** 
1. 用图片查看器打开 PNG，背景应该是透明/棋盘格
2. 用代码检查：
   ```python
   from PIL import Image
   img = Image.open("cutout.png")
   assert img.mode == "RGBA", "Should be RGBA"
   # 检查是否有透明像素
   alpha = img.split()[3]
   transparent_pixels = sum(1 for p in alpha.getdata() if p == 0)
   print(f"Transparent pixels: {transparent_pixels}")
   ```

### Q: 测试 endpoint 在生产环境会暴露吗？

**A:** 不会。测试路由只在 `ENABLE_TEST_ROUTES=true` 时启用。生产环境不要设置此环境变量。

### Q: 如何测试 API key 错误场景？

**A:** 使用错误的 API key 调用 API，应该返回 401 错误。

---

## 📚 相关文件

- `app/services/segmentation/third_party_provider.py`: Provider 实现
- `app/routers/test_segmentation.py`: 测试 endpoint
- `scripts/test_third_party_segmentation.py`: 测试脚本
- `tests/test_third_party_segmentation.py`: 自动化测试
