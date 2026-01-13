def test_health(client):
    r = client.get("/pipeline/v1/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert "rembg" in j
