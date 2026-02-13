# 步骤 4 验证：模块拆分与重构

## ✅ 已完成的工作

### 1. TemplateResolver 实现

**文件**: `app/services/template_resolver.py`

**功能**:
- ✅ 模板下载（从 URL 下载 zip 文件）
- ✅ 校验和验证（SHA256）
- ✅ 模板解压（解压到缓存目录）
- ✅ 缓存机制（避免重复下载）
- ✅ 错误处理（自定义异常类）

**关键方法**:
- `resolve()`: 主入口，下载、验证、解压模板
- `_download_template()`: 下载模板文件
- `_validate_checksum()`: 验证 SHA256 校验和
- `_extract_template()`: 解压模板并验证 manifest.json

**缓存路径**: `{PIPELINE_DATA_DIR}/templates/{template_code}/{version}/`

---

### 2. RenderEngine 实现

**文件**: `app/services/render_engine.py`

**功能**:
- ✅ 画布创建（从背景图或尺寸配置）
- ✅ 单个照片应用（兼容 safeArea 方式）
- ✅ 多个照片应用（photos 配置）
- ✅ 贴纸应用（stickers 配置）
- ✅ 完整渲染流程

**关键方法**:
- `render()`: 主入口，完整渲染流程
- `_create_canvas()`: 创建画布
- `_apply_single_photo()`: 应用单个照片（兼容旧方式）
- `apply_photos()`: 应用多个照片
- `apply_stickers()`: 应用贴纸

**从 compose_service.py 迁移的逻辑**:
- ✅ `fit_or_fill()` 图像调整逻辑
- ✅ `alpha_composite()` 图像合成逻辑
- ✅ safeArea 处理逻辑
- ✅ overlay 处理逻辑（迁移到 stickers）

---

## 🧪 验证方法

### 方法 1：快速测试脚本（推荐）

```powershell
cd D:\workspace\image-pipeline
python scripts\quick_test_modules.py
```

**预期输出**:
```
============================================================
快速模块测试验证
============================================================

============================================================
测试 TemplateResolver
============================================================
✅ TemplateResolver 初始化成功
   - template_code: tpl_001
   - version: 0.1.0
   ...

============================================================
测试 RenderEngine
============================================================
✅ 创建示例图像: (200, 200), mode=RGB
✅ 从尺寸创建画布: (800, 600), mode=RGBA
✅ 应用单个照片: (800, 600)
✅ 应用多个照片: (800, 600)
✅ 完整渲染: (800, 600)

✅ 所有测试通过！
```

---

### 方法 2：运行单元测试

```powershell
cd D:\workspace\image-pipeline
pytest tests/test_template_resolver.py tests/test_render_engine.py -v
```

**预期输出**:
```
test_template_resolver.py::test_template_resolver_init PASSED
test_template_resolver.py::test_template_resolver_checksum_validation PASSED
test_template_resolver.py::test_template_extraction PASSED
test_template_resolver.py::test_template_resolver_cache_dir_creation PASSED

test_render_engine.py::test_render_engine_init PASSED
test_render_engine.py::test_render_engine_create_canvas_from_size PASSED
test_render_engine.py::test_render_engine_create_canvas_from_background PASSED
test_render_engine.py::test_render_engine_apply_single_photo PASSED
test_render_engine.py::test_render_engine_apply_photos PASSED
test_render_engine.py::test_render_engine_apply_stickers PASSED
test_render_engine.py::test_render_engine_full_render PASSED
test_render_engine.py::test_render_engine_render_with_photos PASSED
```

---

### 方法 3：手动测试 TemplateResolver（需要 HTTP 服务器）

**前提条件**:
1. 准备一个模板 zip 文件（包含 manifest.json）
2. 启动一个简单的 HTTP 服务器提供下载

**测试步骤**:

1. **准备测试模板**:
   ```powershell
   # 创建测试模板目录
   mkdir test_template
   cd test_template
   
   # 创建 manifest.json
   echo '{"outputWidth": 1800, "outputHeight": 1200}' > manifest.json
   
   # 创建 zip 文件
   Compress-Archive -Path * -DestinationPath ..\test_template.zip
   ```

2. **启动 HTTP 服务器**:
   ```powershell
   # 在包含 test_template.zip 的目录中
   python -m http.server 9000
   ```

3. **计算校验和**:
   ```powershell
   # PowerShell
   $hash = Get-FileHash test_template.zip -Algorithm SHA256
   echo $hash.Hash
   ```

4. **测试下载**:
   ```python
   from app.services.template_resolver import TemplateResolver
   
   resolver = TemplateResolver(
       template_code="test_tpl",
       version="1.0.0",
       download_url="http://127.0.0.1:9000/test_template.zip",
       checksum="你的SHA256值",
   )
   
   template_dir = resolver.resolve()
   print(f"模板目录: {template_dir}")
   ```

---

### 方法 4：手动测试 RenderEngine

```python
from PIL import Image
from app.services.render_engine import RenderEngine

# 创建测试图像
test_image = Image.new("RGB", (500, 500), color=(255, 0, 0))  # 红色

# 测试 1: 使用 safeArea
manifest1 = {
    "outputWidth": 1800,
    "outputHeight": 1200,
    "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
    "cropMode": "FILL",
}

engine1 = RenderEngine(manifest1)
result1 = engine1.render(test_image.convert("RGBA"))
result1.save("test_output_1.png")
print(f"✅ 输出: test_output_1.png ({result1.size})")

# 测试 2: 使用 photos 配置
manifest2 = {
    "outputWidth": 1800,
    "outputHeight": 1200,
    "photos": [
        {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "cropMode": "FILL"},
    ],
}

engine2 = RenderEngine(manifest2)
result2 = engine2.render(test_image.convert("RGBA"))
result2.save("test_output_2.png")
print(f"✅ 输出: test_output_2.png ({result2.size})")
```

---

## 📋 验证清单

### TemplateResolver
- [x] 可以初始化
- [x] 可以设置缓存目录
- [x] 可以下载模板（需要 HTTP 服务器）
- [x] 可以验证校验和
- [x] 可以解压模板
- [x] 可以检测 manifest.json
- [x] 支持缓存机制（避免重复下载）

### RenderEngine
- [x] 可以从尺寸创建画布
- [x] 可以从背景图创建画布
- [x] 可以应用单个照片（safeArea）
- [x] 可以应用多个照片（photos 配置）
- [x] 可以应用贴纸（stickers 配置）
- [x] 可以完整渲染流程
- [x] 支持 FIT 和 FILL 裁剪模式

---

## 🔍 代码对比

### 从 compose_service.py 迁移的逻辑

**原代码** (`compose_service.py`):
```python
def compose(self, bg, person_rgba, overlay_path, safe_area, crop_mode):
    canvas = bg.convert("RGBA")
    sx = int(W * safe_area["x"])
    sy = int(H * safe_area["y"])
    placed = fit_or_fill(person_rgba, sw, sh, crop_mode)
    canvas.alpha_composite(placed, (sx, sy))
    if overlay_path:
        ov = open_image(overlay_path)
        canvas.alpha_composite(ov, (0, 0))
    return canvas
```

**新代码** (`render_engine.py`):
- ✅ `_apply_single_photo()`: 实现了相同的 safeArea 逻辑
- ✅ `apply_stickers()`: 实现了 overlay 逻辑（支持多个贴纸）
- ✅ `apply_photos()`: 新增支持多个照片位置
- ✅ `_create_canvas()`: 新增从背景图或尺寸创建画布

---

## 📝 总结

**步骤 4 已完成** ✅

- ✅ TemplateResolver: 实现了模板下载、校验、解压功能
- ✅ RenderEngine: 从 compose_service 迁移了渲染逻辑，并扩展支持多照片和贴纸
- ✅ 模块化: 每个模块职责单一，可以独立测试
- ✅ 单元测试: 创建了完整的测试用例
- ✅ 快速测试: 提供了快速验证脚本

**下一步**:
1. 实现 ManifestLoader 模块（加载和验证 manifest.json）
2. 实现 StorageManager 模块（存储图像并返回 URL）
3. 在路由中集成所有模块，完成完整的图像处理流程
