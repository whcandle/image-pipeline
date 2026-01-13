import os

def test_process_missing_raw(client):
    payload = {
        "requestId": "req_x",
        "sessionId": "sess_x",
        "attemptIndex": 0,
        "rawPath": "D:/no_such_raw.jpg",
        "template": {
            "templateId": "tpl",
            "outputWidth": 300,
            "outputHeight": 200,
            "backgroundPath": "D:/no_such_bg.jpg",
            "overlayPath": "D:/no_such_ov.png",
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
            "cropMode": "FILL",
        },
        "options": {"bgMode": "STATIC", "segmentation": "OFF", "featherPx": 0, "strength": 0.6},
        "output": {"previewWidth": 200, "finalWidth": 300},
    }
    r = client.post("/pipeline/v1/process", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "INVALID_INPUT"
