import json
from datetime import datetime, timezone


def log_event(event: str, **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False))
