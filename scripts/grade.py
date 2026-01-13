import json
import sys
import time
import requests

BASE = "http://localhost:9002"

# ======= 你可以在这里改成本机真实 raw 图片路径 =======
RAW = r"D:\workspace\image-pipeline\app\data\swim.jpg"

RUBRIC = [
    ("Health endpoint", 10),
    ("Process success", 25),
    ("Steps contains 3 items", 10),
    ("Static files accessible", 15),
    ("Invalid rawPath handled", 15),
    ("Invalid safeArea handled", 15),
    ("Overlay/bg missing should not crash", 10),
]

def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)

def post_process(payload):
    r = requests.post(f"{BASE}/pipeline/v1/process", json=payload, timeout=30)
    ok(r.status_code == 200, f"process http {r.status_code}")
    return r.json()

def get_json(path):
    r = requests.get(f"{BASE}{path}", timeout=10)
    ok(r.status_code == 200, f"GET {path} -> {r.status_code}")
    return r.json()

def get_file(url):
    r = requests.get(url, timeout=20)
    ok(r.status_code == 200, f"GET file -> {r.status_code}")
    ok(len(r.content) > 1000, "file too small, may be empty")
    return True

def main():
    score = 0
    detail = []

    # 1) health
    try:
        j = get_json("/pipeline/v1/health")
        ok(j.get("ok") is True, "health ok != true")
        detail.append(("Health endpoint", True))
        score += 10
    except Exception as e:
        detail.append(("Health endpoint", False, str(e)))

    # 2) process success (bg/overlay missing should not crash)
    payload_ok = {
        "requestId": "req_grade_001",
        "sessionId": "sess_grade_001",
        "attemptIndex": 0,
        "rawPath": RAW,
        "template": {
            "templateId": "tpl_test",
            "outputWidth": 1800,
            "outputHeight": 1200,
            "backgroundPath": r"D:\no_such_bg.jpg",
            "overlayPath": r"D:\no_such_ov.png",
            "safeArea": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8},
            "cropMode": "FILL",
        },
        "options": {"bgMode": "STATIC", "segmentation": "AUTO", "featherPx": 6, "strength": 0.6},
        "output": {"previewWidth": 900, "finalWidth": 1800},
    }

    try:
        j = post_process(payload_ok)
        ok(j.get("ok") is True, "process ok != true")
        ok(j.get("previewUrl"), "missing previewUrl")
        ok(j.get("finalUrl"), "missing finalUrl")
        detail.append(("Process success", True))
        score += 25

        # overlay/bg missing should not crash (already tested by missing path)
        detail.append(("Overlay/bg missing should not crash", True))
        score += 10

        # 3) steps contains 3 items
        steps = j.get("steps", [])
        ok(len(steps) == 3, f"steps len != 3, got {len(steps)}")
        names = [s["name"] for s in steps]
        ok(names == ["SEGMENT", "BACKGROUND", "COMPOSE"], f"steps names mismatch: {names}")
        detail.append(("Steps contains 3 items", True))
        score += 10

        # 4) static files accessible
        get_file(j["previewUrl"])
        get_file(j["finalUrl"])
        detail.append(("Static files accessible", True))
        score += 15

    except Exception as e:
        detail.append(("Process success", False, str(e)))

    # 5) invalid rawPath handled
    try:
        payload_bad_raw = dict(payload_ok)
        payload_bad_raw["requestId"] = "req_grade_badraw"
        payload_bad_raw["sessionId"] = "sess_grade_badraw"
        payload_bad_raw["rawPath"] = r"D:\no_such_raw.jpg"
        j = post_process(payload_bad_raw)
        ok(j.get("ok") is False, "bad raw should ok=false")
        err = j.get("error", {})
        ok(err.get("code") == "INVALID_INPUT", f"bad raw error code {err.get('code')}")
        detail.append(("Invalid rawPath handled", True))
        score += 15
    except Exception as e:
        detail.append(("Invalid rawPath handled", False, str(e)))

    # 6) invalid safeArea handled
    try:
        payload_bad_sa = json.loads(json.dumps(payload_ok))
        payload_bad_sa["requestId"] = "req_grade_badsa"
        payload_bad_sa["sessionId"] = "sess_grade_badsa"
        payload_bad_sa["template"]["safeArea"] = {"x": 0.9, "y": 0.9, "w": 0.5, "h": 0.5}  # x+w>1
        j = post_process(payload_bad_sa)
        # FastAPI/Pydantic 会直接 422 或者我们的 handler 返回 error
        # 这里接受 422 也算通过（说明校验生效）
        # 但我们用 requests.post 已经强制 200 check，所以改为直接请求一次不走 post_process
        detail.append(("Invalid safeArea handled", False, "unexpected path"))
    except AssertionError:
        # 走到这里说明 post_process 的 status_code check 失败（422）
        detail.append(("Invalid safeArea handled", True))
        score += 15
    except Exception as e:
        detail.append(("Invalid safeArea handled", False, str(e)))

    # 输出结果
    print("======== SCORE ========")
    print(f"Total: {score}/100")
    for item in detail:
        print(item)

    # 退出码：<60 认为不及格
    sys.exit(0 if score >= 60 else 2)

if __name__ == "__main__":
    main()
