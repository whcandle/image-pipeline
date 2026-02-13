# Pipeline V2 API 参数说明

## 请求参数详解

### `/pipeline/v2/process` 接口参数说明

#### 1. `templateCode` (模板代码)
- **类型**: `string`
- **含义**: 模板的唯一标识符
- **示例**: `"tpl_001"`
- **业务场景**: 
  - 前端选择了一个模板（如"毕业照模板"、"证件照模板"）
  - 后端需要知道用哪个模板来合成图像
  - 类似商品ID，用于标识不同的模板

#### 2. `versionSemver` (版本号)
- **类型**: `string` (语义化版本格式)
- **含义**: 模板的版本号
- **示例**: `"0.1.0"` 或 `"1.2.3"`
- **格式**: `主版本号.次版本号.修订号` (如 `1.0.0`)
- **业务场景**:
  - 模板可能会更新（修复bug、优化布局）
  - 需要指定使用哪个版本的模板
  - 确保使用正确的模板版本，避免兼容性问题

#### 3. `downloadUrl` (下载地址)
- **类型**: `string` (URL)
- **含义**: 模板压缩包的下载地址
- **示例**: `"http://example.com/tpl_001_0.1.0.zip"`
- **业务场景**:
  - 模板是一个压缩包（包含背景图、贴纸、配置文件等）
  - 系统需要从这个URL下载模板文件
  - 下载后解压，读取其中的 `manifest.json` 配置文件

#### 4. `checksumSha256` (校验和)
- **类型**: `string` (可选)
- **含义**: 模板文件的 SHA256 哈希值，用于验证文件完整性
- **示例**: `"abc123..."` (64个字符的十六进制字符串)
- **业务场景**:
  - 下载文件后，计算文件的 SHA256 值
  - 与提供的 `checksumSha256` 对比
  - 如果不一致，说明文件损坏或被篡改，拒绝使用
  - **安全措施**：防止使用错误的或恶意的模板文件

#### 5. `rawPath` (原始图像路径)
- **类型**: `string` (文件路径)
- **含义**: 用户上传的原始照片的本地路径
- **示例**: `"D:/some/image.png"` 或 `"/data/uploads/user_photo.jpg"`
- **业务场景**:
  - 用户拍照或上传照片后，照片保存在服务器某个位置
  - 这个路径指向那张原始照片
  - 系统会读取这张照片，然后根据模板配置进行合成

---

## 完整业务流程

```
1. 用户选择模板
   ↓
2. 前端发送请求，包含：
   - templateCode: "tpl_001"          ← 要用的模板
   - versionSemver: "0.1.0"            ← 模板版本
   - downloadUrl: "http://..."         ← 模板下载地址
   - checksumSha256: "abc123..."       ← 校验和（可选）
   - rawPath: "D:/photos/user.jpg"     ← 用户照片路径
   ↓
3. 后端处理：
   a) TemplateResolver: 下载模板，验证校验和，解压
   b) ManifestLoader: 读取 manifest.json（模板配置）
   c) RenderEngine: 根据配置合成图像
      - 把用户照片放到模板的指定位置
      - 添加贴纸、背景等
   d) StorageManager: 保存合成后的图像，返回URL
   ↓
4. 返回结果：
   {
     "finalUrl": "http://example.com/files/final_123.jpg"
   }
```

---

## 测试目的

### 当前阶段（骨架实现）的测试目标：

1. **验证路由注册**
   - ✅ 接口 `/pipeline/v2/process` 是否存在
   - ✅ 能否正常接收 POST 请求

2. **验证参数解析**
   - ✅ 请求体能否正确解析为 `PipelineV2Request` 对象
   - ✅ 必填参数验证是否工作（缺少参数会报错）

3. **验证服务模块调用**
   - ✅ 四个服务模块（TemplateResolver、ManifestLoader、RenderEngine、StorageManager）能否正常实例化
   - ✅ 不会因为导入错误或语法错误导致崩溃

4. **验证响应格式**
   - ✅ 返回的 JSON 包含 `finalUrl` 字段
   - ✅ 响应状态码为 200

### 后续阶段（完整实现）的测试目标：

- 真实下载模板并验证校验和
- 读取并解析 manifest.json
- 实际合成图像
- 保存图像并返回真实URL

---

## 实际使用示例

### 场景：用户拍了一张毕业照，想用"毕业照模板"合成

```json
{
  "templateCode": "graduation_photo_001",
  "versionSemver": "2.1.0",
  "downloadUrl": "https://cdn.example.com/templates/graduation_photo_001_v2.1.0.zip",
  "checksumSha256": "a1b2c3d4e5f6...",
  "rawPath": "D:/workspace/image-pipeline/app/data/uploads/session_123/raw_photo.jpg"
}
```

**处理流程**：
1. 下载 `graduation_photo_001_v2.1.0.zip`
2. 验证 SHA256 是否为 `a1b2c3d4e5f6...`
3. 解压，读取 `manifest.json`（里面定义了照片位置、贴纸位置等）
4. 读取 `raw_photo.jpg`
5. 根据 manifest 配置合成图像
6. 保存为 `final_123.jpg`，返回 URL

---

## 注意事项

- **`checksumSha256` 是可选的**：如果提供，会验证；如果不提供，跳过验证
- **`rawPath` 必须是服务器本地路径**：不能是 URL，必须是文件系统路径
- **`downloadUrl` 必须是可访问的**：系统会尝试下载这个文件
- **版本号格式**：必须符合语义化版本规范（如 `1.0.0`，不能是 `v1.0` 或 `1.0`）
