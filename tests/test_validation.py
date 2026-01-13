import pytest

def test_safe_area_invalid(client):
    payload = {
        "requestId": "req_t",
        "sessionId": "sess_t",
        "attemptIndex": 0,
        "rawPath": "D:/no_such.jpg",
        "template": {
            "templateId": "tpl",
            "outputWidth": 100,
            "outputHeight": 100,
            "backgroundPath": None,
            "overlayPath": None,
            "safeArea": {"x": 0.9, "y": 0.9, "w": 0.5, "h": 0.5},
            "cropMode": "FILL",
        },
        "options": {"bgMode": "STATIC", "segmentation": "OFF", "featherPx": 0, "strength": 0.6},
        "output": {"previewWidth": 100, "finalWidth": 100},
    }
    r = client.post("/pipeline/v1/process", json=payload)
    assert r.status_code == 422
