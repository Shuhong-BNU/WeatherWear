from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weatherwear.support.runtime_storage import LOGS_DIR, ensure_runtime_directories, log_file


STRUCTURED_LOG_NAME = "app.events.jsonl"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _label_for_source(source: str) -> str:
    labels = {
        "api.out.log": "API stdout",
        "api.err.log": "API stderr",
        "web.out.log": "Web stdout",
        "web.err.log": "Web stderr",
        STRUCTURED_LOG_NAME: "App Events",
    }
    return labels.get(source, source)


def record_runtime_event(
    event_type: str,
    message: str,
    *,
    level: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    ensure_runtime_directories()
    event = {
        "timestamp": _utc_now(),
        "type": event_type,
        "level": level,
        "message": message,
        "payload": payload or {},
    }
    path = log_file(STRUCTURED_LOG_NAME)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def list_log_sources() -> list[dict[str, Any]]:
    ensure_runtime_directories()
    sources: list[dict[str, Any]] = []
    for path in sorted(LOGS_DIR.glob("*.*")):
        if not path.is_file():
            continue
        stat = path.stat()
        sources.append(
            {
                "source": path.name,
                "label": _label_for_source(path.name),
                "kind": "structured" if path.name.endswith(".jsonl") else "text",
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    if not any(item["source"] == STRUCTURED_LOG_NAME for item in sources):
        sources.append(
            {
                "source": STRUCTURED_LOG_NAME,
                "label": _label_for_source(STRUCTURED_LOG_NAME),
                "kind": "structured",
                "size_bytes": 0,
                "updated_at": "",
            }
        )
    return sources


def _safe_log_path(source: str) -> Path:
    candidate = (LOGS_DIR / source).resolve()
    if candidate.parent != LOGS_DIR.resolve():
        raise ValueError("invalid_log_source")
    return candidate


def read_log_tail(source: str, *, lines: int = 200) -> dict[str, Any]:
    ensure_runtime_directories()
    path = _safe_log_path(source)
    if not path.exists():
        return {"source": source, "kind": "text", "lines": [], "events": []}

    raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    tail = raw_lines[-max(1, min(lines, 1000)) :]
    if path.name.endswith(".jsonl"):
        events: list[dict[str, Any]] = []
        for line in tail:
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return {
            "source": source,
            "kind": "structured",
            "lines": tail,
            "events": events,
        }
    return {
        "source": source,
        "kind": "text",
        "lines": tail,
        "events": [],
    }

