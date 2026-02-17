# SegmentationService 测试指南

## 📋 功能概述

`SegmentationService` 实现了完整的抠图降级逻辑：

1. **Third-party provider** (remove.bg) → 成功则使用
2. **Rembg** → third-party 失败时降级
3. **Raw** → rembg 也失败时降级（根据 `rules.segmentation.fallback`）

**关键特性：**
- 质量检查（`minSubjectAreaRatio`）
- 完整的 notes 记录（`seg.provider`、`seg.fallback`、失败原因）
- 永远出图（fallback=raw 时保证能出图）

## 🧪 测试方法

### 方法 1: 运行 pytest 自动化测试（推荐）

```bash
cd D:\workspace\image-pipeline

# 运行所有 SegmentationService 测试
pytest tests/test_segmentation_service.py -v
```

**测试覆盖：**

1. ✅ `test_segmentation_third_party_success`: third-party 成功场景
2. ✅ `test_segmentation_fallback_to_rembg`: third-party 失败，降级到 rembg
3. ✅ `test_segmentation_fallback_to_raw`: third-party 和 rembg 都失败，降级到 raw
4. ✅ `test_segmentation_quality_check_fails`: 质量检查失败，降级到 rembg

---

### 方法 2: 通过 v2 process API 测试（真实场景）

#### 场景 1: removebg 正常

**准备：**
- 确保 platform 正常，能返回 removebg execution plan
- 确保 removebg API key 有效

**测试命令：**
```bash
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d "{
    \"templateCode\": \"tpl_002\",
    \"versionSemver\": \"0.1.2\",
    \"downloadUrl\": \"http://127.0.0.1:9000/tpl_002_v0.1.2.zip\",
    \"checksumSha256\": \"f909e74b3432be726507abd70f794d2259f3ab199ef609557d45ade377b6f126\",
    \"rawPath\": \"D:/AICreama/imagePipeLineTmp/test.jpg\"
  }"
```

**验证：**
- 检查 response.notes，应该包含：
  - `seg.provider` with `provider: "removebg"`
  - 不应该有 `seg.fallback`

---

#### 场景 2: removebg endpoint 错误（降级到 rembg）

**准备：**
- 临时修改 `app/clients/platform_client.py` 中的 endpoint，或
- 在 platform 中配置错误的 endpoint

**方法 A: 临时修改代码（仅测试）**
```python
# 在 app/clients/platform_client.py 的 resolve 方法中
# 临时修改 endpoint（仅用于测试）
if "removebg" in execution_plan.get("providerCode", "").lower():
    execution_plan["endpoint"] = "https://invalid-endpoint.example.com/removebg"
```

**方法 B: 使用错误的 API key**
- 在 platform 配置中设置错误的 removebg API key

**测试命令：**（同上）

**验证：**
- 检查 response.notes，应该包含：
  - `SEG_THIRD_PARTY_FAIL`
  - `seg.fallback` with `fallback: "rembg"`
  - `seg.provider` with `provider: "rembg"`
- 应该能正常出图（使用 rembg 结果）

---

#### 场景 3: rembg 禁用/异常（降级到 raw）

**准备：**
- 临时禁用 rembg（卸载包或修改代码）

**方法 A: 临时修改代码（仅测试）**
```python
# 在 app/services/segment_service.py 中
def segment_auto(self, img_rgba: Image.Image, feather_px: int) -> Tuple[Image.Image, Optional[str]]:
    # 临时强制返回错误
    return img_rgba, "rembg_disabled_for_testing"
```

**方法 B: 卸载 rembg**
```bash
pip uninstall rembg
```

**测试命令：**（同上）

**验证：**
- 检查 response.notes，应该包含：
  - `SEG_THIRD_PARTY_FAIL` 或 `SEG_REMBG_FAIL`
  - `seg.fallback` with `fallback: "raw"`
  - `seg.provider` with `provider: "raw"`
- **必须能正常出图**（使用原始图片，没有抠图）

---

## ✅ 验证清单

### 场景 1: removebg 正常
- [x] response.ok = true
- [x] notes 包含 `seg.provider=removebg`
- [x] 没有 `seg.fallback`
- [x] 输出图片有透明背景（如果模板需要）

### 场景 2: removebg 失败，降级 rembg
- [x] response.ok = true（**关键：不能 500**）
- [x] notes 包含 `SEG_THIRD_PARTY_FAIL`
- [x] notes 包含 `seg.fallback=rembg`
- [x] notes 包含 `seg.provider=rembg`
- [x] 输出图片正常（使用 rembg 结果）

### 场景 3: rembg 也失败，降级 raw
- [x] response.ok = true（**关键：必须能出图**）
- [x] notes 包含 `SEG_REMBG_FAIL`
- [x] notes 包含 `seg.fallback=raw`
- [x] notes 包含 `seg.provider=raw`
- [x] 输出图片正常（使用原始图片，没有抠图）

---

## 🔍 调试技巧

### 1. 查看完整的 notes

```python
import json
response = requests.post(...)
notes = response.json()["notes"]
for note in notes:
    print(f"{note['code']}: {note.get('details', {})}")
```

### 2. 检查 timing

```python
timing = response.json()["timing"]
for step in timing["steps"]:
    if step["name"] == "SEGMENTATION":
        print(f"Segmentation took {step['ms']}ms")
```

### 3. 验证图片模式

```python
from PIL import Image
import requests

response = requests.get(final_url)
img = Image.open(io.BytesIO(response.content))
print(f"Image mode: {img.mode}")  # 应该是 RGBA
```

---

## 📝 Notes 格式说明

### seg.provider
```json
{
  "code": "seg.provider",
  "message": "Segmentation provider: third_party",
  "details": {
    "provider": "removebg|rembg|raw",
    "subjectAreaRatio": 0.85  // 仅 third-party 成功时有
  }
}
```

### seg.fallback
```json
{
  "code": "seg.fallback",
  "message": "Fallback to rembg",
  "details": {
    "fallback": "rembg|raw",
    "reason": "http_401|quality_low|exception:..."
  }
}
```

### SEG_THIRD_PARTY_FAIL
```json
{
  "code": "SEG_THIRD_PARTY_FAIL",
  "message": "Third-party segmentation failed: http_401",
  "details": {
    "reason": "http_401|quality_low|exception:..."
  }
}
```

### SEG_REMBG_FAIL
```json
{
  "code": "SEG_REMBG_FAIL",
  "message": "Rembg segmentation failed: rembg_failed:...",
  "details": {
    "reason": "rembg_failed:..."
  }
}
```

---

## 🚨 常见问题

### Q: 为什么降级到 raw 后还能出图？

**A:** 这是设计目标。`fallback=raw` 时，即使所有抠图方法都失败，也应该能出图（使用原始图片）。这避免了"客户看到失败"的情况。

### Q: 如何验证质量检查是否生效？

**A:** 创建一个几乎全透明的图片（主体区域很小），应该会触发质量检查失败，降级到 rembg。

### Q: notes 中会包含 API key 吗？

**A:** 不会。所有 notes 都经过过滤，不会包含敏感信息（如 API key）。

---

## 📚 相关文件

- `app/services/segmentation/segmentation_service.py`: 服务实现
- `app/services/segmentation/third_party_provider.py`: Third-party provider
- `app/services/segment_service.py`: Rembg provider
- `app/routers/process.py`: v2 process 集成
- `tests/test_segmentation_service.py`: 自动化测试
