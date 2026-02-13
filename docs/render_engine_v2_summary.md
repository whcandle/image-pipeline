# RenderEngine v2 实现总结

## ✅ 已完成功能

### 1. RenderEngine 重写

**主要变化**:
- 从接受 `manifest` 改为接受 `runtime_spec`（从 `ManifestLoader.to_runtime_spec()` 返回）
- 简化接口，专注于渲染功能
- 支持按 z 排序图层
- 支持照片的 fit 模式（cover/contain）
- 支持贴纸的旋转和透明度

**核心方法**:

1. **`__init__(runtime_spec: Dict[str, Any])`**
   - 接受 runtime_spec 字典
   - 不再需要 template_dir（因为 runtime_spec 中路径已经是绝对路径）

2. **`render(raw_image: Image.Image) -> Image.Image`**
   - 创建画布（output.width/height）
   - 渲染背景（background.path）
   - 收集所有图层（photos + stickers）并按 z 排序
   - 渲染每个图层
   - 返回最终图像（RGBA 模式）

3. **`_render_photo(canvas, photo, raw_image)`**
   - 渲染照片到画布
   - 支持 fit=cover（FILL）和 fit=contain（FIT）
   - 使用 `fit_or_fill()` 工具函数

4. **`_render_sticker(canvas, sticker)`**
   - 渲染贴纸到画布
   - 支持 resize、rotate、opacity
   - 使用 alpha_composite 合成

---

## 📋 Runtime Spec 结构

RenderEngine 期望的 runtime_spec 结构：

```python
{
    "output": {
        "width": 1800,
        "height": 1200,
        "format": "png"
    },
    "background": {
        "path": "绝对路径"
    },
    "photos": [
        {
            "id": "p1",
            "source": "raw",
            "x": 100,  # 像素坐标
            "y": 200,  # 像素坐标
            "w": 800,  # 像素尺寸
            "h": 900,  # 像素尺寸
            "fit": "cover",  # "cover" 或 "contain"
            "z": 0
        }
    ],
    "stickers": [
        {
            "id": "s1",
            "path": "绝对路径",
            "x": 50,  # 像素坐标
            "y": 50,  # 像素坐标
            "w": 100,  # 像素尺寸
            "h": 100,  # 像素尺寸
            "rotate": 0,  # 旋转角度（度）
            "opacity": 1.0,  # 透明度（0.0-1.0）
            "z": 0
        }
    ]
}
```

---

## 🎯 功能特性

### 1. z 排序

- 所有图层（photos + stickers）按 z 值排序
- 低 z 值在前，先渲染（在底层）
- 高 z 值在后，后渲染（在上层）

### 2. 照片渲染

- 支持 `fit=cover`（FILL 模式）：填满目标区域，可能有裁剪
- 支持 `fit=contain`（FIT 模式）：完整显示图像，可能有留白
- 使用 `fit_or_fill()` 工具函数处理缩放和裁剪

### 3. 贴纸渲染

- 支持 resize（根据 w/h）
- 支持 rotate（旋转角度，度）
- 支持 opacity（透明度，0.0-1.0）
- 使用 alpha_composite 合成

### 4. 错误处理

- 背景文件不存在：正常处理，只是没有背景
- 贴纸文件不存在：正常处理，只是没有贴纸
- 其他错误：抛出 `RenderError`

---

## 🧪 测试文件

### 1. 测试脚本：`scripts/test_render_engine.py`

**功能**:
- 测试基本渲染功能
- 测试 z 排序功能
- 测试 fit 模式（cover/contain）
- 测试贴纸的旋转和透明度
- 测试坐标改变导致输出变化

**测试用例**:
1. `test_render_basic()`: 基本渲染功能
2. `test_render_z_order()`: z 排序功能
3. `test_render_fit_modes()`: fit 模式
4. `test_render_sticker_rotate_opacity()`: 贴纸的旋转和透明度
5. `test_render_coordinate_change()`: 改变坐标，输出图像应该变化

**输出**:
- 每个测试都会生成输出图像，用于手动检查

---

### 2. pytest 测试：`tests/test_render_engine_v2.py`

**功能**:
- 自动测试渲染功能
- 使用临时目录和文件，不依赖真实文件系统

**测试用例**:
1. `test_render_basic`: 基本渲染功能
2. `test_render_z_order`: z 排序功能
3. `test_render_fit_cover`: fit=cover 模式
4. `test_render_fit_contain`: fit=contain 模式
5. `test_render_sticker_rotate`: 贴纸旋转
6. `test_render_sticker_opacity`: 贴纸透明度
7. `test_render_coordinate_change`: 坐标改变
8. `test_render_missing_background`: 背景文件不存在
9. `test_render_missing_sticker`: 贴纸文件不存在

---

## 🧪 测试方法

### 方法 1: 运行测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\test_render_engine.py
```

**预期输出**:
```
============================================================
RenderEngine 渲染功能测试
============================================================

============================================================
测试 1: 基本渲染功能
============================================================
[OK] 输出尺寸正确: (1800, 1200)
[OK] 输出模式正确: RGBA
[OK] 输出图像已保存: C:\...\output_basic.png

[OK] 测试 1 通过：基本渲染功能正常

...

============================================================
[OK] 所有测试通过！
============================================================

提示：请手动检查生成的输出图像，确认渲染效果符合预期。
```

**输出文件**:
- `output_basic.png`: 基本渲染结果
- `output_z_order.png`: z 排序测试结果
- `output_fit_modes.png`: fit 模式测试结果
- `output_rotate_opacity.png`: 旋转和透明度测试结果
- `output_coord1.png` / `output_coord2.png`: 坐标改变测试结果

---

### 方法 2: 运行 pytest 测试（自动测试）

```powershell
pytest tests/test_render_engine_v2.py -v
```

**预期输出**:
```
test_render_engine_v2.py::test_render_basic PASSED
test_render_engine_v2.py::test_render_z_order PASSED
test_render_engine_v2.py::test_render_fit_cover PASSED
test_render_engine_v2.py::test_render_fit_contain PASSED
test_render_engine_v2.py::test_render_sticker_rotate PASSED
test_render_engine_v2.py::test_render_sticker_opacity PASSED
test_render_engine_v2.py::test_render_coordinate_change PASSED
test_render_engine_v2.py::test_render_missing_background PASSED
test_render_engine_v2.py::test_render_missing_sticker PASSED

9 passed
```

---

### 方法 3: 手动测试

```python
from app.services.render_engine import RenderEngine
from PIL import Image

# 创建 runtime_spec（从 ManifestLoader.to_runtime_spec() 获取）
runtime_spec = {
    "output": {"width": 1800, "height": 1200, "format": "png"},
    "background": {"path": "绝对路径"},
    "photos": [...],
    "stickers": [...]
}

# 创建 RenderEngine
engine = RenderEngine(runtime_spec)

# 加载 raw_image
raw_image = Image.open("raw_image.jpg")

# 渲染
result = engine.render(raw_image)

# 保存结果
result.save("output.png")
```

---

## 📋 验证清单

- [x] 重写 `RenderEngine.render()` 方法，使用 runtime_spec 格式
- [x] 实现按 z 排序图层功能
- [x] 实现照片渲染（支持 fit=cover/contain）
- [x] 实现贴纸渲染（支持 rotate 和 opacity）
- [x] 创建画布（output.width/height）
- [x] 渲染背景（background.path）
- [x] 循环 photos[] 和 stickers[]（按 z 排序）
- [x] 输出合成图像（RGBA 模式）
- [x] 测试脚本：基本渲染功能
- [x] 测试脚本：z 排序功能
- [x] 测试脚本：fit 模式
- [x] 测试脚本：贴纸的旋转和透明度
- [x] 测试脚本：坐标改变导致输出变化
- [x] pytest 测试：9 个测试用例

---

## 🔍 关键实现细节

### 1. z 排序实现

```python
# 收集所有图层
layers = []
for photo in self.runtime_spec.get("photos", []):
    layers.append({"type": "photo", "data": photo})
for sticker in self.runtime_spec.get("stickers", []):
    layers.append({"type": "sticker", "data": sticker})

# 按 z 排序（低 z 值在前，先渲染）
layers.sort(key=lambda x: x["data"].get("z", 0))

# 渲染每个图层
for layer in layers:
    if layer["type"] == "photo":
        self._render_photo(canvas, layer["data"], raw_image)
    elif layer["type"] == "sticker":
        self._render_sticker(canvas, layer["data"])
```

### 2. fit 模式转换

```python
# cover -> FILL, contain -> FIT
crop_mode = "FILL" if fit_mode == "cover" else "FIT"
placed = fit_or_fill(raw_image.convert("RGBA"), w, h, crop_mode)
```

### 3. 贴纸旋转和透明度

```python
# 应用旋转
if rotate != 0:
    sticker_img = sticker_img.rotate(-rotate, expand=True)

# 应用透明度
if opacity < 1.0:
    alpha = sticker_img.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    sticker_img.putalpha(alpha)
```

---

## ✅ 验收标准

根据需求，Step 3 的验收标准：

- [x] ✅ 实现 `RenderEngine.render()` 方法
- [x] ✅ 创建画布（output.width/height）
- [x] ✅ 画背景（background.path）
- [x] ✅ 循环 photos[]（只支持 source=raw）
- [x] ✅ 循环 stickers[]（png alpha paste）
- [x] ✅ 按 z 排序图层
- [x] ✅ 支持 fit=cover/contain
- [x] ✅ 支持 rotate 和 opacity
- [x] ✅ 测试脚本：固定一张 raw，改 manifest 里的坐标，输出图像是否变化
- [x] ✅ 验证：看到图"变了"，说明系统已经真正活了

**结论**: Step 3 已完成 ✅

---

## 🔄 下一步

Step 4: 集成所有模块到 `/pipeline/v2/process` 路由，完成真实的图像处理流程。

---

## 📊 测试结果

**测试脚本**: ✅ 5 个测试用例全部通过
- test_render_basic: 基本渲染功能
- test_render_z_order: z 排序功能
- test_render_fit_modes: fit 模式
- test_render_sticker_rotate_opacity: 贴纸的旋转和透明度
- test_render_coordinate_change: 坐标改变导致输出变化

**pytest 测试**: ✅ 9 个测试用例全部通过
- test_render_basic
- test_render_z_order
- test_render_fit_cover
- test_render_fit_contain
- test_render_sticker_rotate
- test_render_sticker_opacity
- test_render_coordinate_change
- test_render_missing_background
- test_render_missing_sticker
