from __future__ import annotations

from typing import Any

from weatherwear.support.env_manager import env_manager
from weatherwear.support.logs_support import record_runtime_event
from weatherwear.support.llm_support import refresh_env


DEFAULT_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
DEFAULT_ATTRIBUTION = "&copy; OpenStreetMap contributors"
DEFAULT_CENTER_LAT = 39.9042
DEFAULT_CENTER_LON = 116.4074
DEFAULT_ZOOM = 9


def _read_float(key: str, fallback: float) -> float:
    raw = env_manager.get_value(key, str(fallback)) or str(fallback)
    try:
        return float(raw)
    except ValueError:
        return fallback


def _read_int(key: str, fallback: int) -> int:
    raw = env_manager.get_value(key, str(fallback)) or str(fallback)
    try:
        return int(raw)
    except ValueError:
        return fallback


def build_map_settings_response() -> dict[str, Any]:
    provider = (env_manager.get_value("MAP_PROVIDER", "osm") or "osm").strip().lower()
    if provider not in {"osm", "baidu"}:
        provider = "osm"
    baidu_ak = env_manager.get_value("BAIDU_MAP_AK", "") or ""
    return {
        "provider": provider,
        "baidu_ak": baidu_ak,
        "baidu_ak_configured": bool(baidu_ak),
        "osm_tile_url": env_manager.get_value("OSM_TILE_URL", DEFAULT_TILE_URL) or DEFAULT_TILE_URL,
        "osm_attribution": env_manager.get_value("OSM_ATTRIBUTION", DEFAULT_ATTRIBUTION) or DEFAULT_ATTRIBUTION,
        "default_center_lat": _read_float("MAP_DEFAULT_CENTER_LAT", DEFAULT_CENTER_LAT),
        "default_center_lon": _read_float("MAP_DEFAULT_CENTER_LON", DEFAULT_CENTER_LON),
        "default_zoom": _read_int("MAP_DEFAULT_ZOOM", DEFAULT_ZOOM),
    }


def update_map_settings(payload: dict[str, Any]) -> dict[str, Any]:
    provider = str(payload.get("provider", "osm")).strip().lower()
    if provider not in {"osm", "baidu"}:
        provider = "osm"
    updates = {
        "MAP_PROVIDER": provider,
        "BAIDU_MAP_AK": str(payload.get("baidu_ak", "") or "").strip(),
        "OSM_TILE_URL": str(payload.get("osm_tile_url", DEFAULT_TILE_URL) or DEFAULT_TILE_URL).strip(),
        "OSM_ATTRIBUTION": str(payload.get("osm_attribution", DEFAULT_ATTRIBUTION) or DEFAULT_ATTRIBUTION).strip(),
        "MAP_DEFAULT_CENTER_LAT": str(payload.get("default_center_lat", DEFAULT_CENTER_LAT)).strip(),
        "MAP_DEFAULT_CENTER_LON": str(payload.get("default_center_lon", DEFAULT_CENTER_LON)).strip(),
        "MAP_DEFAULT_ZOOM": str(payload.get("default_zoom", DEFAULT_ZOOM)).strip(),
    }
    if not env_manager.apply_changes(updates=updates):
        raise RuntimeError("failed_to_update_map_settings")
    refresh_env(override=True)
    response = build_map_settings_response()
    record_runtime_event(
        "map.settings.updated",
        "Map settings updated.",
        payload={"provider": response["provider"]},
    )
    return response


def test_map_settings(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = build_map_settings_response()
    merged.update(payload or {})
    provider = str(merged.get("provider", "osm")).strip().lower()
    if provider == "baidu":
        ak = str(merged.get("baidu_ak", "") or "").strip()
        ok = bool(ak)
        return {
            "ok": ok,
            "message": (
                "Baidu map key is stored. Runtime rendering still depends on Baidu browser authorization."
                if ok
                else "Missing Baidu map key."
            ),
            "provider": provider,
        }
    tile_url = str(merged.get("osm_tile_url", DEFAULT_TILE_URL) or "").strip()
    ok = bool(tile_url)
    return {
        "ok": ok,
        "message": "OSM tile configuration is ready." if ok else "Missing OSM tile URL.",
        "provider": "osm",
    }
