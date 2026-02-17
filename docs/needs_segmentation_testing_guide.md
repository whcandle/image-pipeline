# needs_segmentation 判定逻辑测试指南

## 📋 功能概述

在 v2 process 流程中加入 `needs_segmentation` 判定逻辑：

- `needs_cutout = any(photo.source == "cutout")`
- `seg_enabled = rules.segmentation.enabled == true`（默认 false）
- `needs_segmentation = needs_cutout && seg_enabled`

判定结果会写入 `response.notes`，包含：
- `NEEDS_CUTOUT`: 是否需要 cutout
- `SEG_ENABLED`: rules 中 segmentation 是否启用
- `NEEDS_SEGMENTATION`: 最终是否需要 segmentation

## 🧪 测试方法

### 方法 1: 运行 pytest 自动化测试（推荐）

```bash
cd D:\workspace\image-pipeline

# 运行所有 needs_segmentation 测试
pytest tests/test_needs_segmentation.py -v

# 运行单个测试
pytest tests/test_needs_segmentation.py::test_needs_segmentation_source_raw -v
pytest tests/test_needs_segmentation.py::test_needs_segmentation_source_cutout_disabled -v
pytest tests/test_needs_segmentation.py::test_needs_segmentation_source_cutout_enabled -v
pytest tests/test_needs_segmentation.py::test_needs_segmentation_multiple_photos -v
```

**测试场景覆盖：**

1. ✅ `test_needs_segmentation_source_raw`: source=raw，needs_cutout=false
2. ✅ `test_needs_segmentation_source_cutout_disabled`: source=cutout 但 rules.enabled=false，needs_segmentation=false
3. ✅ `test_needs_segmentation_source_cutout_enabled`: source=cutout 且 rules.enabled=true，needs_segmentation=true
4. ✅ `test_needs_segmentation_multiple_photos`: 多个 photos，其中一个 source=cutout

---

### 方法 2: 手动测试脚本

```bash
cd D:\workspace\image-pipeline
python scripts/test_needs_segmentation_manual.py
```

这个脚本会测试：
- 默认 rules 加载
- needs_segmentation 判定逻辑（4 种场景）
- 从文件加载 rules（可选）

---

### 方法 3: 通过 API 手动测试

#### 场景 1: source=raw（needs_cutout=false）

**准备模板：**
- manifest.json 中 `compose.photos[].source = "raw"`

**调用 API：**
```bash
curl -X POST http://localhost:9002/pipeline/v2/process \
  -H "Content-Type: application/json" \
  -d '{
    "templateCode": "tpl_test",
    "versionSemver": "0.1.0",
    "downloadUrl": "http://example.com/template.zip",
    "checksumSha256": "...",
    "rawPath": "D:/path/to/raw.jpg"
  }'
```

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_CUTOUT",
      "details": {"value": false}
    },
    {
      "code": "SEG_ENABLED",
      "details": {"value": false}
    },
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": false}
    }
  ]
}
```

---

#### 场景 2: source=cutout 但 rules.enabled=false

**准备模板：**
- manifest.json 中 `compose.photos[].source = "cutout"`
- **不创建** `assets/rules.json`（使用默认 rules，enabled=false）

**调用 API：**（同上）

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_CUTOUT",
      "details": {"value": true}
    },
    {
      "code": "SEG_ENABLED",
      "details": {"value": false}
    },
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": false}  // needs_cutout=true 但 seg_enabled=false
    }
  ]
}
```

---

#### 场景 3: source=cutout 且 rules.enabled=true

**准备模板：**
- manifest.json 中 `compose.photos[].source = "cutout"`
- 创建 `assets/rules.json`：
```json
{
  "segmentation.enabled": true,
  "segmentation.prefer": ["removebg"],
  "segmentation.timeoutMs": 5000
}
```

**调用 API：**（同上）

**验证响应 notes：**
```json
{
  "notes": [
    {
      "code": "NEEDS_CUTOUT",
      "details": {"value": true}
    },
    {
      "code": "SEG_ENABLED",
      "details": {"value": true}
    },
    {
      "code": "NEEDS_SEGMENTATION",
      "details": {"value": true}  // needs_cutout=true && seg_enabled=true
    }
  ]
}
```

---

## ✅ 验证清单

### 场景 1: source=raw
- [x] `needs_cutout = false`
- [x] `seg_enabled = false`（默认）
- [x] `needs_segmentation = false`
- [x] 流程正常完成（ok=true）
- [x] 渲染正常（和以前一样，走 raw 模式）

### 场景 2: source=cutout 但 rules.enabled=false
- [x] `needs_cutout = true`
- [x] `seg_enabled = false`（默认）
- [x] `needs_segmentation = false`
- [x] 流程正常完成（ok=true）
- [x] 仍走 raw 模式出图（不进入抠图链路）

### 场景 3: source=cutout 且 rules.enabled=true
- [x] `needs_cutout = true`
- [x] `seg_enabled = true`（从 rules.json 读取）
- [x] `needs_segmentation = true`
- [x] 流程正常完成（ok=true）
- [x] notes 中标记需要 segmentation（但暂不实际调用，只记录）

### 场景 4: 多个 photos
- [x] 如果任何一个 photo 的 `source == "cutout"`，则 `needs_cutout = true`
- [x] 判定逻辑正确

---

## 📝 注意事项

1. **不破坏现有功能**：所有判定逻辑只写入 notes，不改变渲染/合成逻辑
2. **默认行为**：如果没有 `rules.json`，使用默认 rules（`segmentation.enabled = false`）
3. **错误处理**：如果 `rules.json` 解析失败，自动回退到默认 rules，不中断流程
4. **不调用第三方**：当前只做判定，不实际调用抠图服务

---

## 🔍 调试技巧

如果测试失败，检查：

1. **notes 是否正确写入**：
   ```python
   notes = {note["code"]: note for note in response.json()["notes"]}
   print(notes.get("NEEDS_CUTOUT"))
   print(notes.get("SEG_ENABLED"))
   print(notes.get("NEEDS_SEGMENTATION"))
   ```

2. **rules 是否正确加载**：
   ```python
   print(notes.get("RULES_LOADED"))
   print(notes.get("RULES_DEFAULT_USED"))
   ```

3. **photos source 是否正确**：
   ```python
   # 在 process.py 中打印
   print(f"photos: {runtime_spec.get('photos')}")
   print(f"needs_cutout: {needs_cutout}")
   ```

---

## 📚 相关文件

- `app/services/rules_loader.py`: Rules 加载器
- `app/routers/process.py`: v2 process 主流程（包含判定逻辑）
- `tests/test_needs_segmentation.py`: 自动化测试
- `scripts/test_needs_segmentation_manual.py`: 手动测试脚本
