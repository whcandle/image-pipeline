from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_process_ok(sample_images):
    app = create_app()
    client = TestClient(app)

    payload = {
        "requestId": "req_test_1",
        "sessionId": "sess_123",
        "attemptIndex": 0,
        "rawPath": sample_images["raw_path"],
        "template": {
            "templateId": "tpl_001",
            "outputWidth": 1800,
            "outputHeight": 1200,
            "backgroundPath": sample_images["bg_path"],
            "overlayPath": sample_images["overlay_path"],
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
            "cropMode": "FILL",
        },
        "options": {"bgMode": "STATIC", "segmentation": "OFF", "featherPx": 6, "strength": 0.6},
        "output": {"previewWidth": 900, "finalWidth": 1800},
    }

    r = client.post("/pipeline/v1/process", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "previewUrl" in data and "finalUrl" in data
    assert [s["name"] for s in data["steps"]] == ["SEGMENT", "BACKGROUND", "COMPOSE"]

    # check static files route responds (preview)
    preview_path = data["previewUrl"].split("http://localhost:9002")[-1]
    r2 = client.get(preview_path)
    assert r2.status_code == 200


def test_process_missing_raw(sample_images):
    app = create_app()
    client = TestClient(app)

    payload = {
        "requestId": "req_test_2",
        "sessionId": "sess_404",
        "attemptIndex": 0,
        "rawPath": sample_images["raw_path"] + ".missing",
        "template": {
            "templateId": "tpl_001",
            "outputWidth": 1800,
            "outputHeight": 1200,
            "backgroundPath": sample_images["bg_path"],
            "overlayPath": sample_images["overlay_path"],
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
            "cropMode": "FILL",
        },
    }

    r = client.post("/pipeline/v1/process", json=payload)
    assert r.status_code == 400
    data = r.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_INPUT"
