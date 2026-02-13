# Image Pipeline Service

图像处理管道服务，提供模板驱动的图像合成功能。

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9002
```

### 健康检查

```bash
curl http://localhost:9002/health
```

## API 接口

### 接口约定

**重要**: 所有接口和路径约定已定死，详见 [API_CONVENTIONS.md](./docs/API_CONVENTIONS.md)

### 核心接口

- **POST `/pipeline/v2/process`**: 模板驱动的图像处理接口
- **GET `/files/preview/**`**: 预览图静态文件服务
- **GET `/files/final/**`**: 最终图静态文件服务

详细文档: [API_CONVENTIONS.md](./docs/API_CONVENTIONS.md)

## 项目结构

```
app/
├── services/          # 核心服务模块
│   ├── template_resolver.py    # 模板解析器
│   ├── manifest_loader.py       # Manifest 加载器
│   ├── render_engine.py         # 渲染引擎
│   └── storage_manager.py       # 存储管理器
├── routers/           # API 路由
│   └── process.py     # 处理接口
└── config.py          # 配置管理

tests/                 # 测试文件
scripts/               # 测试脚本
docs/                  # 文档
```

## 模块说明

### TemplateResolver

负责模板下载、缓存、校验和解压。

### ManifestLoader

负责加载和校验 manifest.json，生成 runtime_spec。

### RenderEngine

根据 runtime_spec 渲染合成图像。

### StorageManager

负责图像存储和 URL 生成。

## 测试

### 运行所有测试

```bash
pytest -v
```

### 运行特定模块测试

```bash
pytest tests/test_storage_manager.py -v
```

### 冒烟测试

```bash
python scripts/test_storage_manager_smoke.py
```

## 配置

配置文件: `app/config.py`

环境变量支持（通过 `.env` 文件）:
- `BOOTH_DATA_DIR`: 本地存储根目录（默认: `D:\AICreama\booth\data`）
- `TEMPLATE_CACHE_DIR`: 模板缓存目录（默认: `app/data/_templates`）
- `PUBLIC_BASE_URL`: 公共访问基础 URL（默认: `http://localhost:9002`）

## 文档

- [API 接口约定](./docs/API_CONVENTIONS.md) - 接口和路径约定（**必读**）
- [V2 API 参数说明](./docs/v2_api_parameters_explained.md) - API 参数详解
- [V2 API 响应示例](./docs/v2_api_response_examples.md) - 成功和失败响应 JSON 示例

## 开发规范

1. 所有接口路径必须遵循 [API_CONVENTIONS.md](./docs/API_CONVENTIONS.md) 的约定
2. 模块化设计，单一职责原则
3. 完整的单元测试和集成测试
4. 错误前置，早失败原则
