from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


_LOCK = Lock()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
STATE_DIR = RUNTIME_DIR / "state"
LOGS_DIR = RUNTIME_DIR / "logs"


def ensure_runtime_directories() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def state_file(name: str) -> Path:
    ensure_runtime_directories()
    return STATE_DIR / name


def log_file(name: str) -> Path:
    ensure_runtime_directories()
    return LOGS_DIR / name


def read_json(path: Path, default: Any) -> Any:
    ensure_runtime_directories()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    ensure_runtime_directories()
    with _LOCK:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

