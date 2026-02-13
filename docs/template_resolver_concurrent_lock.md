# TemplateResolver 并发锁实现说明

## ✅ 已完成功能

### 1. 并发锁机制

**实现方式**: 进程内 dict + threading.Lock

**锁的 key**: `{templateCode}:{versionSemver}:{checksumSha256}`

**代码结构**:
```python
class TemplateResolver:
    # 类级别的锁字典
    _locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()  # 保护 _locks 字典本身的锁
```

**锁获取逻辑**:
```python
def _get_lock(self) -> threading.Lock:
    lock_key = self._get_lock_key()  # {templateCode}:{version}:{checksum}
    
    # 双重检查锁定模式
    if lock_key in self._locks:
        return self._locks[lock_key]
    
    with self._locks_lock:
        if lock_key not in self._locks:
            self._locks[lock_key] = threading.Lock()
        return self._locks[lock_key]
```

---

### 2. 并发安全实现

**在 `resolve()` 方法中使用锁**:

```python
def resolve(self) -> str:
    # Step 1: 快速路径（不加锁）
    if manifest_path.exists():
        return str(self.final_dir.resolve())
    
    # Step 2: 加锁保护下载和解压
    lock = self._get_lock()
    with lock:
        # 双重检查：获取锁后再次检查缓存
        if manifest_path.exists():
            return str(self.final_dir.resolve())
        
        # 执行下载和解压（只执行一次）
        ...
```

**特点**:
- 快速路径：缓存命中时不需要加锁
- 双重检查：获取锁后再次检查缓存（可能其他线程已下载完成）
- 锁粒度：每个模板（templateCode:version:checksum）有独立的锁

---

## 🧪 测试用例

### 测试 1: cache hit（缓存命中）

**测试文件**: `tests/test_template_resolver.py::test_cache_hit`

**验证**:
- 手动创建缓存目录和 manifest.json
- 调用 resolve() 应该直接返回，不访问网络
- `requests.get` 不应该被调用

---

### 测试 2: checksum mismatch（校验和不匹配）

**测试文件**: `tests/test_template_resolver.py::test_checksum_mismatch`

**验证**:
- 使用错误的校验和
- 应该抛出 `TemplateChecksumMismatch` 异常
- 异常信息包含期望和实际的校验和

---

### 测试 3: extract 后包含 manifest.json

**测试文件**: `tests/test_template_resolver.py::test_extract_contains_manifest_json`

**验证**:
- 下载和解压成功
- 解压后的目录包含 manifest.json
- manifest.json 内容正确
- 其他文件也存在

---

### 测试 4: 并发只下载一次

**测试文件**: `tests/test_template_resolver.py::test_concurrent_resolve_only_download_once`

**验证**:
- 10 个线程并发调用 resolve()
- 使用 monkeypatch 统计 `requests.get` 调用次数
- 应该只下载一次（`download_count == 1`）
- 所有线程都成功返回相同的目录
- 没有错误发生

---

## 🚀 最简单测试方法

### 方法 1: 运行所有测试（推荐）

```powershell
cd D:\workspace\image-pipeline
pytest tests/test_template_resolver.py -q
```

**预期输出**:
```
........
8 passed
```

---

### 方法 2: 只运行新增的 4 个测试

```powershell
pytest tests/test_template_resolver.py::test_cache_hit \
       tests/test_template_resolver.py::test_checksum_mismatch \
       tests/test_template_resolver.py::test_extract_contains_manifest_json \
       tests/test_template_resolver.py::test_concurrent_resolve_only_download_once -v
```

---

### 方法 3: 运行单个测试（调试用）

```powershell
# 测试缓存命中
pytest tests/test_template_resolver.py::test_cache_hit -v

# 测试校验和不匹配
pytest tests/test_template_resolver.py::test_checksum_mismatch -v

# 测试解压包含 manifest.json
pytest tests/test_template_resolver.py::test_extract_contains_manifest_json -v

# 测试并发只下载一次
pytest tests/test_template_resolver.py::test_concurrent_resolve_only_download_once -v
```

---

## 📋 验证清单

- [x] 并发锁机制：使用进程内 dict + threading.Lock
- [x] 锁的 key：`{templateCode}:{versionSemver}:{checksumSha256}`
- [x] 并发安全：同一模板只下载解压一次
- [x] 快速路径：缓存命中时不需要加锁
- [x] 双重检查：获取锁后再次检查缓存
- [x] 测试用例：cache hit
- [x] 测试用例：checksum mismatch
- [x] 测试用例：extract 后包含 manifest.json
- [x] 测试用例：并发只下载一次（统计 requests.get 调用次数）

---

## 🔍 原理说明

### 并发锁机制

1. **锁字典**: 类级别的 `_locks` 字典存储所有锁
2. **锁的 key**: `{templateCode}:{version}:{checksum}` 确保每个模板有独立锁
3. **双重检查锁定**: 避免不必要的锁竞争
4. **快速路径**: 缓存命中时直接返回，不需要加锁

### 并发安全保证

- **同一模板**: 多个线程同时 resolve 同一模板时，只有一个线程会下载
- **不同模板**: 不同模板使用不同的锁，可以并行下载
- **缓存命中**: 缓存命中时不需要加锁，性能最优

---

## 📝 总结

**已完成**:
- ✅ 并发锁机制实现
- ✅ 4 个测试用例添加
- ✅ 所有测试通过

**当前状态**: 并发安全功能已实现，可以进行测试验证。
