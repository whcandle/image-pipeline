"""
测试 Pipeline V2 API (/pipeline/v2/process)

验证：
1. 路由是否正确注册
2. 参数解析是否正常
3. 响应格式是否正确
"""


def test_process_v2_smoke(client):
    """
    简单冒烟测试：验证 /pipeline/v2/process 路由存在且能返回 finalUrl 字段。
    """
    payload = {
        "templateCode": "tpl_001",
        "versionSemver": "0.1.0",
        "downloadUrl": "http://example.com/tpl_001_0.1.0.zip",
        "checksumSha256": "dummy_checksum",
        "rawPath": "D:/some/raw/image.png",
    }

    r = client.post("/pipeline/v2/process", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}. Response: {r.text}"

    j = r.json()
    assert "finalUrl" in j, f"Response missing 'finalUrl' field: {j}"
    assert isinstance(j["finalUrl"], str), f"'finalUrl' should be string, got {type(j['finalUrl'])}"


def test_process_v2_without_checksum(client):
    """
    测试可选参数 checksumSha256（不提供时应该也能正常工作）
    """
    payload = {
        "templateCode": "tpl_002",
        "versionSemver": "1.0.0",
        "downloadUrl": "http://example.com/tpl_002_v1.0.0.zip",
        # checksumSha256 不提供，应该是可选的
        "rawPath": "D:/some/raw/image.png",
    }

    r = client.post("/pipeline/v2/process", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}. Response: {r.text}"

    j = r.json()
    assert "finalUrl" in j


def test_process_v2_missing_required_field(client):
    """
    测试缺少必填参数时应该返回 422 验证错误
    """
    payload = {
        "templateCode": "tpl_001",
        # 缺少 versionSemver
        "downloadUrl": "http://example.com/tpl_001.zip",
        "rawPath": "D:/some/raw/image.png",
    }

    r = client.post("/pipeline/v2/process", json=payload)
    assert r.status_code == 422, f"Expected 422 (validation error), got {r.status_code}. Response: {r.text}"


def test_process_v2_real_request(client):
    """
    使用真实的测试参数（模拟用户实际请求）
    """
    payload = {
        "templateCode": "tpl_001",
        "versionSemver": "0.1.1",
        "downloadUrl": "http://127.0.0.1:9000/tpl_001_v0.1.1.zip",
        "checksumSha256": "f288dad7df1564584cf4e2eb4c9d5a5bf9d8d79a5566d8aa230a46673ff0ed1d",
        "rawPath": "D:/AICreama/imagePipeLineTmp/test.jpg",
    }

    r = client.post("/pipeline/v2/process", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}. Response: {r.text}"

    j = r.json()
    assert "finalUrl" in j
    assert j["finalUrl"] == "/files/v2/placeholder.png"  # 当前占位实现返回固定值
