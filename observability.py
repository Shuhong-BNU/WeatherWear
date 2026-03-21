from __future__ import annotations

import json
import threading
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any


_LOCK = threading.Lock()
_COUNTERS: Counter[str] = Counter()


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def record_metric(name: str, amount: int = 1):
    with _LOCK:
        _COUNTERS[name] += amount


def metrics_snapshot() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)


def log_event(event: str, **fields: Any):
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    try:
        print(json.dumps(payload, ensure_ascii=False))
    except Exception:
        print(str(payload))
