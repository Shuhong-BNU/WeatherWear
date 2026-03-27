from __future__ import annotations

import json
import os
import sys
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


def _should_emit_stdout_events() -> bool:
    if os.getenv("WEATHERWEAR_SILENCE_STDOUT_EVENTS", "").strip() == "1":
        return False
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    if "pytest" in sys.modules or "unittest" in sys.modules:
        return False
    return True


def log_event(event: str, **fields: Any):
    if not _should_emit_stdout_events():
        return
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "type": event,
        "level": str(fields.pop("level", "info") or "info"),
        "message": str(fields.pop("message", event) or event),
        "payload": fields,
    }
    try:
        print(json.dumps(payload, ensure_ascii=False))
    except Exception:
        print(str(payload))
