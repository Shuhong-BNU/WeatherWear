from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException, Request, Response

from weatherwear.support.env_manager import env_manager


COOKIE_NAME = "weatherwear_dev_session"
COOKIE_MAX_AGE = 60 * 60 * 12


def _secret() -> str:
    return env_manager.get_value("WEATHERWEAR_SESSION_SECRET", "weatherwear-dev-secret") or "weatherwear-dev-secret"


def is_developer_pin_required() -> bool:
    return bool((env_manager.get_value("WEATHERWEAR_DEV_PIN", "") or "").strip())


def _configured_pin() -> str:
    return (env_manager.get_value("WEATHERWEAR_DEV_PIN", "") or "").strip()


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii")
    signature = hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def _decode(token: str) -> dict[str, Any] | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        raw = base64.urlsafe_b64decode(body.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload


def create_developer_cookie() -> str:
    return _encode(
        {
            "scope": "developer",
            "exp": int(time.time()) + COOKIE_MAX_AGE,
        }
    )


def set_developer_cookie(response: Response) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_developer_cookie(),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_developer_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def has_developer_access(request: Request) -> bool:
    if not is_developer_pin_required():
        return True
    token = request.cookies.get(COOKIE_NAME, "")
    payload = _decode(token) if token else None
    return bool(payload and payload.get("scope") == "developer")


def require_developer_access(request: Request) -> None:
    if not has_developer_access(request):
        raise HTTPException(status_code=403, detail="developer_unlock_required")


def unlock_developer_access(pin: str) -> bool:
    configured = _configured_pin()
    if not configured:
        return True
    return hmac.compare_digest(configured, str(pin).strip())


def get_developer_session_state(request: Request) -> dict[str, Any]:
    return {
        "required": is_developer_pin_required(),
        "unlocked": has_developer_access(request),
    }
