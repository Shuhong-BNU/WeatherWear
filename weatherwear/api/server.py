from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from weatherwear.api.schemas import (
    ClientLogEventRequest,
    ClientLogEventResponse,
    DeveloperSessionResponse,
    DeveloperUnlockRequest,
    FavoriteCreateRequest,
    FavoriteItem,
    LocaleCode,
    LogSource,
    LogTailResponse,
    MapSettingsResponse,
    MapSettingsTestResponse,
    MapSettingsUpdateRequest,
    ModelConnectionTestResponse,
    ModelSettingsResponse,
    ModelSettingsTestRequest,
    ModelSettingsUpdateRequest,
    HistoryCreateRequest,
    HistoryItem,
    QueryRequest,
    QueryCancelRequest,
    QueryCancelResponse,
    QueryResponse,
)
from weatherwear.application.presentation import build_result_view_model
from weatherwear.application.coordinator import MultiAgentCoordinator
from weatherwear.support.cancellation import query_cancellation_registry
from weatherwear.support.dev_auth import (
    clear_developer_cookie,
    get_developer_session_state,
    require_developer_access,
    set_developer_cookie,
    unlock_developer_access,
)
from weatherwear.support.health_check import gather_runtime_health
from weatherwear.support.llm_support import (
    build_model_settings_response,
    get_embedding_health,
    probe_embedding_health,
    test_embedding_provider,
    test_model_provider,
    update_model_settings,
)
from weatherwear.support.logs_support import list_log_sources, read_log_tail, record_runtime_event
from weatherwear.support.map_support import (
    build_map_settings_response,
    test_map_settings,
    update_map_settings,
)
from weatherwear.support.observability import new_request_id
from weatherwear.support.user_state_store import (
    create_history_item,
    delete_history_item,
    delete_favorite_item,
    list_favorite_items,
    list_history_items,
    save_favorite_item,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        health = probe_embedding_health(force=True)
        record_runtime_event(
            "model.embedding.health_checked",
            "Embedding health checked on startup.",
            payload=health,
        )
    except Exception as exc:
        record_runtime_event(
            "model.embedding.health_checked",
            "Embedding health check failed on startup.",
            level="warning",
            payload={"status": "degraded", "degrade_reason": str(exc)},
        )
    yield


app = FastAPI(title="WeatherWear API", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

coordinator = MultiAgentCoordinator()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _trace_tags(record: Any) -> list[str]:
    tags = ["agent"]
    node_name = str(getattr(record, "node_name", "") or "")
    provider = str(getattr(record, "provider", "") or "")
    name = str(getattr(record, "name", "") or "")
    decision_reason = str(getattr(record, "decision_reason", "") or "")

    if getattr(record, "used_llm", False):
        tags.append("llm")
    if node_name in {"retrieve_knowledge", "retrieve_knowledge_rules", "retrieve_knowledge_vector", "rerank_knowledge", "apply_knowledge"}:
        tags.append("rag")
    if name == "MapPinResolver" or provider == "reverse_geocoding" or decision_reason == "map_pin_selected":
        tags.append("map")
    if node_name == "fetch_weather":
        tags.append("weather")
    if node_name == "generate_outfit":
        tags.append("fashion")
    return list(dict.fromkeys(tags))


def _default_embedding_settings_payload() -> dict[str, Any]:
    return {
        "enabled": False,
        "inherit_from_chat_provider": False,
        "provider": "openai_compatible",
        "base_url": "",
        "model": "",
        "proxy_url": "",
        "timeout_seconds": 60,
        "missing_fields": ["base_url", "model", "api_key"],
        "has_api_key": False,
        "runtime_provider": "",
        "runtime_base_url": "",
        "runtime_proxy_url": "",
        "embedding_fingerprint": "",
        "health": {"status": "unknown"},
    }


def _normalize_model_settings_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    embedding = normalized.get("embedding")
    if not isinstance(embedding, dict):
        normalized["embedding"] = _default_embedding_settings_payload()
    return normalized


def _emit_query_step_events(result: Any, view_model: dict[str, Any]) -> None:
    request_id = str((view_model.get("summary") or {}).get("request_id", "") or "")
    for index, record in enumerate(getattr(result, "execution_trace", []) or [], start=1):
        metadata = getattr(record, "metadata", {})
        record_runtime_event(
            "query.step",
            "WeatherWear query step recorded.",
            payload={
                "request_id": request_id,
                "index": index,
                "step": str(getattr(record, "node_name", "") or getattr(record, "name", "") or ""),
                "role": str(getattr(record, "role", "") or ""),
                "name": str(getattr(record, "name", "") or ""),
                "provider": str(getattr(record, "provider", "") or ""),
                "model": str(getattr(record, "model", "") or ""),
                "success": bool(getattr(record, "success", False)),
                "used_llm": bool(getattr(record, "used_llm", False)),
                "fallback_used": bool(getattr(record, "fallback_used", False)),
                "elapsed_ms": int(getattr(record, "elapsed_ms", 0) or 0),
                "cumulative_ms": int(getattr(record, "cumulative_ms", 0) or 0),
                "step_kind": str(getattr(record, "step_kind", "") or ""),
                "retrieval_mode": str(((metadata if isinstance(metadata, dict) else {}) or {}).get("retrieval_mode", "") or ""),
                "vector_leg_skipped_reason": str(((metadata if isinstance(metadata, dict) else {}) or {}).get("vector_leg_skipped_reason", "") or ""),
                "decision_reason": str(getattr(record, "decision_reason", "") or ""),
                "error": str(getattr(record, "error", "") or ""),
                "tags": _trace_tags(record),
                "metadata": metadata if isinstance(metadata, dict) else {},
            },
        )

EXAMPLES = [
    {"label": "北京", "query_text": "北京"},
    {"label": "伦敦 London", "query_text": "伦敦 London"},
    {"label": "Springfield", "query_text": "springfield"},
    {"label": "东京涩谷", "query_text": "东京涩谷"},
    {"label": "复杂输入", "query_text": "帮我查今天东京天气并给穿搭"},
]


def _extract_selected_coords(view_model: dict[str, Any]) -> dict[str, float] | None:
    coords = (view_model.get("summary") or {}).get("selected_coords")
    if isinstance(coords, dict) and coords.get("lat") is not None and coords.get("lon") is not None:
        return {
            "lat": float(coords["lat"]),
            "lon": float(coords["lon"]),
        }
    pin = view_model.get("location_pin") or {}
    if pin.get("lat") is not None and pin.get("lon") is not None:
        return {
            "lat": float(pin["lat"]),
            "lon": float(pin["lon"]),
        }
    return None


def _build_history_payload(view_model: dict[str, Any]) -> dict[str, Any]:
    summary = view_model.get("summary") or {}
    hero = view_model.get("hero_summary") or {}
    weather = view_model.get("weather") or {}
    return {
        "request_id": str(summary.get("request_id", "") or ""),
        "locale": str(summary.get("locale", "zh-CN") or "zh-CN"),
        "query_text": str(summary.get("user_input", "") or ""),
        "gender": str((summary.get("query_context") or {}).get("gender", "neutral") or "neutral"),
        "occasion_text": str((summary.get("query_context") or {}).get("occasion_text", "") or ""),
        "target_date": str((summary.get("query_context") or {}).get("target_date", "") or ""),
        "confirmed_location_label": str(
            summary.get("confirmed_location_label")
            or summary.get("selected_city")
            or ""
        ),
        "location_source": str(summary.get("location_source", "") or ""),
        "confirmation_mode": str(summary.get("confirmation_mode", "smart") or "smart"),
        "query_path": str(hero.get("query_path", "") or ""),
        "headline_advice": str(
            (view_model.get("fashion") or {}).get("headline_advice")
            or hero.get("one_line_advice")
            or ""
        ),
        "weather_summary": str(weather.get("description") or weather.get("daily_range_text") or ""),
        "selected_coords": _extract_selected_coords(view_model),
    }


@app.get("/api/health/runtime")
def get_runtime_health(locale: LocaleCode = "zh-CN") -> dict[str, Any]:
    return gather_runtime_health(locale)


@app.get("/api/examples")
def get_examples() -> dict[str, Any]:
    return {"items": EXAMPLES}


@app.post("/api/query", response_model=QueryResponse)
def query_weatherwear(payload: QueryRequest) -> QueryResponse:
    request_id = payload.client_request_id.strip() or new_request_id()
    coords_dict = payload.selected_coords.model_dump() if payload.selected_coords else None
    location_source = "map_pin" if coords_dict else "text_search"
    user_input = payload.query_text.strip()
    if not user_input and coords_dict:
        user_input = f"{coords_dict['lat']},{coords_dict['lon']}"

    record_runtime_event(
        "query.started",
        "WeatherWear query started.",
        payload={
            "request_id": request_id,
            "user_input": user_input,
            "selected_candidate_id": payload.selected_candidate_id.strip(),
            "locale": payload.locale,
            "confirmation_mode": payload.confirmation_mode,
            "location_source": location_source,
            "gender": payload.gender,
            "occasion_text": payload.occasion_text,
            "target_date": payload.target_date,
        },
    )
    result = coordinator.process_query(
        user_input,
        selected_candidate_id=payload.selected_candidate_id.strip(),
        confirmation_mode=payload.confirmation_mode,
        selected_coords=coords_dict,
        location_source=location_source,
        locale=payload.locale,
        gender=payload.gender,
        occasion_text=payload.occasion_text,
        target_date=payload.target_date,
        request_id=request_id,
    )
    view_model = build_result_view_model(result, locale=payload.locale)
    if result.error != "query_cancelled":
        create_history_item(_build_history_payload(view_model))
    _emit_query_step_events(result, view_model)
    if result.error == "query_cancelled":
        record_runtime_event(
            "query.cancelled",
            "WeatherWear query cancelled.",
            level="warning",
            payload={
                "request_id": view_model.get("summary", {}).get("request_id", ""),
                "location": view_model.get("summary", {}).get("confirmed_location_label", ""),
            },
        )
    else:
        record_runtime_event(
            "query.completed",
            "WeatherWear query completed.",
            payload={
                "ok": result.ok,
                "request_id": view_model.get("summary", {}).get("request_id", ""),
                "location": view_model.get("summary", {}).get("confirmed_location_label", ""),
                "resolution_final_status": view_model.get("summary", {}).get("resolution_final_status", ""),
                "retrieval_mode": view_model.get("summary", {}).get("retrieval_mode", ""),
                "vector_leg_status": view_model.get("summary", {}).get("vector_leg_status", ""),
            },
        )
    return QueryResponse(ok=result.ok, view_model=view_model)


@app.post("/api/query/cancel", response_model=QueryCancelResponse)
def cancel_weatherwear_query(payload: QueryCancelRequest) -> QueryCancelResponse:
    request_id = payload.request_id.strip()
    if not request_id:
        raise HTTPException(status_code=400, detail="missing_request_id")
    query_cancellation_registry.cancel(request_id)
    record_runtime_event(
        "query.cancel.requested",
        "WeatherWear query cancellation requested.",
        level="warning",
        payload={"request_id": request_id},
    )
    return QueryCancelResponse(ok=True)


@app.post("/api/logs/client-event", response_model=ClientLogEventResponse)
def post_client_log_event(payload: ClientLogEventRequest) -> ClientLogEventResponse:
    event_type = payload.type.strip() or "frontend.event"
    message = payload.message.strip() or "Frontend runtime event."
    record_runtime_event(
        event_type,
        message,
        level=payload.level.strip() or "info",
        payload=payload.payload or {},
    )
    return ClientLogEventResponse(ok=True)


@app.get("/api/dev/session", response_model=DeveloperSessionResponse)
def get_developer_session(request: Request) -> DeveloperSessionResponse:
    return DeveloperSessionResponse.model_validate(get_developer_session_state(request))


@app.post("/api/dev/unlock", response_model=DeveloperSessionResponse)
def post_developer_unlock(
    payload: DeveloperUnlockRequest,
    request: Request,
    response: Response,
) -> DeveloperSessionResponse:
    if not unlock_developer_access(payload.pin):
        record_runtime_event("developer.unlock_failed", "Developer unlock failed.", level="warning")
        raise HTTPException(status_code=403, detail="invalid_pin")
    set_developer_cookie(response)
    record_runtime_event("developer.unlocked", "Developer session unlocked.")
    return DeveloperSessionResponse.model_validate(
        {
            "required": get_developer_session_state(request)["required"],
            "unlocked": True,
        }
    )


@app.post("/api/dev/lock", response_model=DeveloperSessionResponse)
def post_developer_lock(
    request: Request,
    response: Response,
) -> DeveloperSessionResponse:
    clear_developer_cookie(response)
    record_runtime_event("developer.locked", "Developer session locked.")
    return DeveloperSessionResponse.model_validate(
        {
            "required": get_developer_session_state(request)["required"],
            "unlocked": False,
        }
    )


@app.get("/api/settings/model", response_model=ModelSettingsResponse)
def get_model_settings(_: None = Depends(require_developer_access)) -> ModelSettingsResponse:
    return ModelSettingsResponse.model_validate(_normalize_model_settings_payload(build_model_settings_response()))


@app.put("/api/settings/model", response_model=ModelSettingsResponse)
def put_model_settings(
    payload: ModelSettingsUpdateRequest,
    _: None = Depends(require_developer_access),
) -> ModelSettingsResponse:
    provider_payload = payload.provider.model_dump(exclude_none=True)
    if payload.embedding:
        provider_payload["embedding"] = payload.embedding.model_dump(exclude_none=True)
    if payload.default_provider:
        provider_payload["default_provider"] = payload.default_provider
    updated = update_model_settings(
        slot=payload.slot,
        payload=provider_payload,
        clear_api_key=payload.clear_api_key,
        clear_embedding_api_key=payload.clear_embedding_api_key,
    )
    record_runtime_event(
        "model.settings.updated",
        "Model settings updated.",
        payload={"slot": payload.slot, "default_provider": updated.get("default_provider", "default")},
    )
    return ModelSettingsResponse.model_validate(_normalize_model_settings_payload(updated))


@app.post("/api/settings/model/test", response_model=ModelConnectionTestResponse)
def post_model_test(
    payload: ModelSettingsTestRequest,
    _: None = Depends(require_developer_access),
) -> ModelConnectionTestResponse:
    if payload.embedding:
        data = test_embedding_provider(payload.embedding.model_dump(exclude_none=True))
    else:
        data = test_model_provider(
            slot=payload.slot,
            payload=payload.provider.model_dump(exclude_none=True) if payload.provider else None,
        )
    record_runtime_event(
        "model.embedding.tested" if payload.embedding else "model.chat.tested",
        "Model connection tested.",
        payload={"slot": payload.slot, "ok": data.get("ok", False), "kind": "embedding" if payload.embedding else "chat"},
    )
    return ModelConnectionTestResponse.model_validate(data)


@app.get("/api/settings/map", response_model=MapSettingsResponse)
def get_map_settings() -> MapSettingsResponse:
    return MapSettingsResponse.model_validate(build_map_settings_response())


@app.put("/api/settings/map", response_model=MapSettingsResponse)
def put_map_settings(
    payload: MapSettingsUpdateRequest,
    _: None = Depends(require_developer_access),
) -> MapSettingsResponse:
    updated = update_map_settings(payload.model_dump(exclude_none=True))
    return MapSettingsResponse.model_validate(updated)


@app.post("/api/settings/map/test", response_model=MapSettingsTestResponse)
def post_map_settings_test(
    payload: MapSettingsUpdateRequest,
    _: None = Depends(require_developer_access),
) -> MapSettingsTestResponse:
    data = test_map_settings(payload.model_dump(exclude_none=True))
    record_runtime_event(
        "map.settings.tested",
        "Map settings tested.",
        payload={"provider": data.get("provider", "osm"), "ok": data.get("ok", False)},
    )
    return MapSettingsTestResponse.model_validate(data)


@app.get("/api/history", response_model=list[HistoryItem])
def get_history() -> list[HistoryItem]:
    return [HistoryItem.model_validate(item) for item in list_history_items()]


@app.post("/api/history", response_model=HistoryItem)
def post_history(payload: HistoryCreateRequest) -> HistoryItem:
    data = payload.model_dump(exclude_none=True)
    if payload.selected_coords:
        data["selected_coords"] = payload.selected_coords.model_dump()
    item = create_history_item(data)
    return HistoryItem.model_validate(item)


@app.delete("/api/history/{item_id}")
def delete_history(item_id: str) -> dict[str, bool]:
    deleted = delete_history_item(item_id)
    if deleted:
        record_runtime_event("history.deleted", "History item deleted.", payload={"id": item_id})
    return {"ok": deleted}


@app.get("/api/favorites", response_model=list[FavoriteItem])
def get_favorites() -> list[FavoriteItem]:
    return [FavoriteItem.model_validate(item) for item in list_favorite_items()]


@app.post("/api/favorites", response_model=FavoriteItem)
def post_favorite(payload: FavoriteCreateRequest) -> FavoriteItem:
    item = save_favorite_item(payload.model_dump(exclude_none=True))
    record_runtime_event("favorites.saved", "Favorite location saved.", payload={"id": item.get("id", "")})
    return FavoriteItem.model_validate(item)


@app.delete("/api/favorites/{item_id}")
def delete_favorite(item_id: str) -> dict[str, bool]:
    deleted = delete_favorite_item(item_id)
    if deleted:
        record_runtime_event("favorites.deleted", "Favorite location deleted.", payload={"id": item_id})
    return {"ok": deleted}


@app.get("/api/logs/sources", response_model=list[LogSource])
def get_log_sources(_: None = Depends(require_developer_access)) -> list[LogSource]:
    return [LogSource.model_validate(item) for item in list_log_sources()]


@app.get("/api/logs/tail", response_model=LogTailResponse)
def get_log_tail(
    source: str,
    lines: int = 200,
    _: None = Depends(require_developer_access),
) -> LogTailResponse:
    try:
        data = read_log_tail(source, lines=lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LogTailResponse.model_validate(data)


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def get_frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")


    @app.get("/{full_path:path}", include_in_schema=False)
    def get_frontend_app(full_path: str) -> FileResponse:
        if not full_path or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


def main():
    import uvicorn

    reload_enabled = os.getenv("UVICORN_RELOAD", "0").strip() == "1"
    api_port = int(os.getenv("WEATHERWEAR_API_PORT", "8000").strip() or "8000")
    uvicorn.run("weatherwear.api.server:app", host="127.0.0.1", port=api_port, reload=reload_enabled)


if __name__ == "__main__":
    main()
