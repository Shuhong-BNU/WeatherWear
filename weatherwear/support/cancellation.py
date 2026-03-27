from __future__ import annotations

import threading
import time
from dataclasses import dataclass


class QueryCancelledError(RuntimeError):
    def __init__(self, request_id: str, stage: str = ""):
        super().__init__(f"query_cancelled:{request_id}:{stage}")
        self.request_id = request_id
        self.stage = stage


@dataclass(frozen=True)
class QueryCancellationToken:
    request_id: str
    registry: "QueryCancellationRegistry"

    def is_cancelled(self) -> bool:
        return self.registry.is_cancelled(self.request_id)

    def raise_if_cancelled(self, stage: str = "") -> None:
        if self.is_cancelled():
            raise QueryCancelledError(self.request_id, stage=stage)


class QueryCancellationRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, float | bool]] = {}
        self._ttl_seconds = 900

    def _cleanup_locked(self, now: float) -> None:
        expired_ids = [
            request_id
            for request_id, entry in self._entries.items()
            if now - float(entry.get("updated_at", now)) > self._ttl_seconds
        ]
        for request_id in expired_ids:
            self._entries.pop(request_id, None)

    def start(self, request_id: str) -> QueryCancellationToken:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            entry = self._entries.get(request_id, {})
            self._entries[request_id] = {
                "cancelled": bool(entry.get("cancelled", False)),
                "updated_at": now,
                "active": True,
            }
        return QueryCancellationToken(request_id=request_id, registry=self)

    def cancel(self, request_id: str) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            entry = self._entries.get(request_id, {})
            was_active = bool(entry.get("active", False))
            self._entries[request_id] = {
                "cancelled": True,
                "updated_at": now,
                "active": was_active,
            }
        return True

    def finish(self, request_id: str) -> None:
        now = time.time()
        with self._lock:
            entry = self._entries.get(request_id)
            if not entry:
                return
            if entry.get("cancelled"):
                self._entries[request_id] = {
                    "cancelled": True,
                    "updated_at": now,
                    "active": False,
                }
                return
            self._entries.pop(request_id, None)

    def is_cancelled(self, request_id: str) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup_locked(now)
            entry = self._entries.get(request_id)
            return bool(entry and entry.get("cancelled", False))


query_cancellation_registry = QueryCancellationRegistry()
