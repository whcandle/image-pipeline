from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any


def log_kv(event: str, **kwargs: Any) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        **kwargs,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
