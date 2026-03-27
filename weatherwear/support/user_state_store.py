from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from weatherwear.support.runtime_storage import read_json, state_file, write_json


HISTORY_FILE = "history.json"
FAVORITES_FILE = "favorites.json"


def _read_items(filename: str) -> list[dict[str, Any]]:
    payload = read_json(state_file(filename), [])
    return payload if isinstance(payload, list) else []


def _write_items(filename: str, items: list[dict[str, Any]]) -> None:
    write_json(state_file(filename), items)


def list_history_items() -> list[dict[str, Any]]:
    return _read_items(HISTORY_FILE)


def create_history_item(payload: dict[str, Any]) -> dict[str, Any]:
    items = _read_items(HISTORY_FILE)
    record = {
        "id": payload.get("id") or str(uuid4()),
        "created_at": payload.get("created_at") or datetime.now(UTC).isoformat(),
        **payload,
    }
    items = [record, *[item for item in items if item.get("id") != record["id"]]][:50]
    _write_items(HISTORY_FILE, items)
    return record


def delete_history_item(item_id: str) -> bool:
    items = _read_items(HISTORY_FILE)
    next_items = [item for item in items if item.get("id") != item_id]
    if len(next_items) == len(items):
        return False
    _write_items(HISTORY_FILE, next_items)
    return True


def list_favorite_items() -> list[dict[str, Any]]:
    return _read_items(FAVORITES_FILE)


def save_favorite_item(payload: dict[str, Any]) -> dict[str, Any]:
    items = _read_items(FAVORITES_FILE)
    record = {
        "id": payload.get("id") or str(uuid4()),
        "added_at": payload.get("added_at") or datetime.now(UTC).isoformat(),
        **payload,
    }
    items = [record, *[item for item in items if item.get("id") != record["id"]]][:50]
    _write_items(FAVORITES_FILE, items)
    return record


def delete_favorite_item(item_id: str) -> bool:
    items = _read_items(FAVORITES_FILE)
    next_items = [item for item in items if item.get("id") != item_id]
    if len(next_items) == len(items):
        return False
    _write_items(FAVORITES_FILE, next_items)
    return True

