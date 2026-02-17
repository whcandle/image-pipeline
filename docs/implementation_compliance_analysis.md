# 实现合规性分析报告

## 📋 对比 ChatGPT 5.2 规范要求

### ✅ 已实现的部分

#### 1. v2 process 基础逻辑
- ✅ `needs_segmentation = needs_cutout && seg_enabled` 判断逻辑正确
- ✅ `RULES_LOADED`、`RULES_DEFAULT_USED` notes 记录
- ✅ `NEEDS_CUTOUT`、`SEG_ENABLED`、`NEEDS_SEGMENTATION` notes 记录
- ✅ `SEG_RESOLVED_PROVIDER` notes 记录（不包含 apiKey）
- ✅ Platform resolve 调用（仅在 `needs_segmentation=true` 时）

#### 2. ThirdPartySegmentationProvider 基础实现
- ✅ remove.bg API 调用（multipart/form-data）
- ✅ Header: `X-Api-Key` 认证
- ✅ 字段: `image_file` 上传
- ✅ 基本参数支持（size、format）
- ✅ 错误处理（HTTP 状态码、响应摘要）
- ✅ **不包含 apiKey 在 notes 中**

#### 3. RulesLoader
- ✅ 支持扁平化和嵌套格式
- ✅ 默认规则回退

---

### ❌ 缺失或不符合的部分

#### 1. **降级逻辑（关键缺失）**

**规范要求：**
```python
if needs_seg:
    try:
        plan = platform_client.resolve(...)
        cutout = third_party_seg_provider.segment(raw, plan, rules)
        if quality_ratio(cutout) < rules.segmentation.minSubjectAreaRatio:
            raise QualityLow("subject too small")
        notes += ["seg.provider=third_party"]
    except Exception as e:
        notes += [f"SEG_THIRD_PARTY_FAIL={short(e)}"]
        try:
            cutout = rembg_provider.segment(raw, rules)
            notes += ["seg.provider=rembg", "seg.fallback=rembg"]
        except Exception as e2:
            notes += [f"SEG_REMBG_FAIL={short(e2)}"]
            if rules.segmentation.fallback == "raw":
                cutout = raw
                notes += ["seg.provider=raw", "seg.fallback=raw"]
            else:
                raise
```

**当前状态：**
- ❌ **v2 process 中完全没有调用 ThirdPartySegmentationProvider**
- ❌ **没有降级到 rembg 的逻辑**
- ❌ **没有降级到 raw 的逻辑**
- ❌ **没有质量检查（minSubjectAreaRatio）**

**影响：** 即使 `needs_segmentation=true` 且 resolve 成功，也没有真正进行抠图。

---

#### 2. **plan.params 适配器（部分缺失）**

**规范要求：**
```python
# Header 适配
api_key_header = plan.params.get("apiKeyHeader", "X-Api-Key")
headers[api_key_header] = plan.auth.apiKey

# multipart 字段映射
fields = {}
fields["format"] = plan.params.get("format", "png")
fields["size"] = plan.params.get("size", "auto")
fields["type"] = plan.params.get("type", "person")
for k in ["crop","bg_color","channels","scale"]:
    if plan.params.get(k) is not None:
        fields[k] = str(plan.params[k])
```

**当前状态：**
- ❌ **硬编码 `X-Api-Key`，不支持 `plan.params.apiKeyHeader`**
- ⚠️ **只支持 `size` 和 `format`，缺少 `type`、`crop`、`bg_color`、`channels`、`scale`**

**影响：** 无法通过平台配置灵活调整 remove.bg 参数。

---

#### 3. **返回格式验证（部分缺失）**

**规范要求：**
```python
if resp.status_code == 200 and resp.headers.get("content-type","").startswith("image/"):
    return resp.content  # png bytes
else:
    # try parse json error
    msg = safe_json_error(resp)
    raise ThirdPartyError(...)
```

**当前状态：**
- ⚠️ **只检查 `status_code == 200`，没有检查 `content-type`**
- ✅ **错误时尝试解析 JSON**

**影响：** 如果 API 返回 200 但不是图片，可能解析失败。

---

#### 4. **Notes 记录不完整**

**规范要求：**
```python
notes += [
    "SEG_RESOLVED_PROVIDER=xxx",
    "seg.provider=third_party/rembg/raw",
    "seg.fallback=rembg/raw",
    "SEG_THIRD_PARTY_FAIL=...",
    "SEG_REMBG_FAIL=..."
]
```

**当前状态：**
- ✅ `SEG_RESOLVED_PROVIDER` 已记录
- ❌ **缺少 `seg.provider` 记录**
- ❌ **缺少 `seg.fallback` 记录**
- ❌ **缺少 `SEG_THIRD_PARTY_FAIL` 记录**
- ❌ **缺少 `SEG_REMBG_FAIL` 记录**

**影响：** 无法追踪实际使用的 provider 和降级路径。

---

#### 5. **质量检查缺失**

**规范要求：**
```python
if quality_ratio(cutout) < rules.segmentation.minSubjectAreaRatio:
    raise QualityLow("subject too small")
```

**当前状态：**
- ❌ **完全没有质量检查逻辑**
- ❌ **没有 `quality_ratio` 函数**

**影响：** 无法检测抠图质量，可能使用质量很差的抠图结果。

---

#### 6. **v2 process 集成缺失**

**规范要求：**
```python
cutout = None
if needs_seg:
    # ... 降级逻辑 ...
final = render_engine.render(raw, manifest, artifacts={"cutout": cutout} if cutout else None)
```

**当前状态：**
- ❌ **v2 process 中完全没有调用 ThirdPartySegmentationProvider**
- ❌ **没有将 cutout 传递给 render_engine**
- ❌ **render_engine 可能不支持 cutout artifacts**

**影响：** 整个 segmentation 流程没有真正集成到 v2 process 中。

---

## 📊 合规性评分

| 类别 | 完成度 | 说明 |
|------|--------|------|
| **基础逻辑** | ✅ 90% | needs_segmentation 判断、notes 记录基本完整 |
| **Platform Resolve** | ✅ 100% | 完全符合要求 |
| **ThirdParty Provider** | ⚠️ 60% | 基础功能有，但缺少适配器和完整验证 |
| **降级逻辑** | ❌ 0% | 完全没有实现 |
| **质量检查** | ❌ 0% | 完全没有实现 |
| **v2 集成** | ❌ 0% | 完全没有集成到 process 流程 |
| **Notes 完整性** | ⚠️ 50% | 基础 notes 有，但缺少 provider/fallback 记录 |

**总体合规性：约 40%**

---

## 🔧 需要修复的关键问题

### 优先级 1（必须修复）
1. **在 v2 process 中集成 ThirdPartySegmentationProvider**
2. **实现降级逻辑（third-party -> rembg -> raw）**
3. **将 cutout 传递给 render_engine**

### 优先级 2（重要）
4. **实现质量检查（minSubjectAreaRatio）**
5. **完善 notes 记录（seg.provider、seg.fallback、失败原因）**
6. **支持 plan.params 完整适配器（apiKeyHeader、所有字段）**

### 优先级 3（优化）
7. **添加 content-type 验证**
8. **优化错误消息（short(e) 函数）**

---

## 📝 建议

当前实现**基础架构正确**，但**关键业务逻辑缺失**。需要：

1. **立即实现降级逻辑**：这是核心功能，必须保证 `fallback=raw` 时能出图
2. **集成到 v2 process**：目前 ThirdPartySegmentationProvider 是独立的，需要真正调用
3. **完善适配器**：支持平台配置的灵活性

建议按照 ChatGPT 5.2 的伪代码逐步实现，确保每个降级路径都有完整的 notes 记录。
