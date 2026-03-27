from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

LocaleCode = Literal["zh-CN", "en-US"]
ProviderSlot = Literal["default", "alternate"]
MapProvider = Literal["osm", "baidu"]


class SelectedCoords(BaseModel):
    lat: float
    lon: float


class QueryRequest(BaseModel):
    query_text: str = ""
    selected_candidate_id: str = ""
    confirmation_mode: Literal["smart", "strict"] = "smart"
    selected_coords: SelectedCoords | None = None
    gender: Literal["male", "female", "neutral"] = "neutral"
    occasion_text: str = ""
    target_date: str = ""
    locale: LocaleCode = "zh-CN"
    client_request_id: str = ""


class QueryResponse(BaseModel):
    ok: bool
    view_model: dict[str, Any]


class QueryCancelRequest(BaseModel):
    request_id: str = ""


class QueryCancelResponse(BaseModel):
    ok: bool


class ClientLogEventRequest(BaseModel):
    type: str
    message: str
    level: str = "info"
    payload: dict[str, Any] | None = None


class ClientLogEventResponse(BaseModel):
    ok: bool


class ModelProviderPayload(BaseModel):
    provider: str | None = None
    name: str | None = None
    base_url: str | None = None
    model: str | None = None
    proxy_url: str | None = None
    temperature: float | None = None
    timeout_seconds: int | None = None
    api_key: str | None = None


class ModelProviderPublic(BaseModel):
    name: str
    provider: str
    base_url: str
    model: str
    proxy_url: str
    temperature: float
    timeout_seconds: int
    enabled: bool
    missing_fields: list[str]
    has_api_key: bool


class EmbeddingSettingsPayload(BaseModel):
    enabled: bool | None = None
    inherit_from_chat_provider: bool | None = None
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    proxy_url: str | None = None
    timeout_seconds: int | None = None
    api_key: str | None = None


class EmbeddingSettingsPublic(BaseModel):
    enabled: bool
    inherit_from_chat_provider: bool
    provider: str
    base_url: str
    model: str
    proxy_url: str
    timeout_seconds: int
    missing_fields: list[str]
    has_api_key: bool
    runtime_provider: str = ""
    runtime_base_url: str = ""
    runtime_proxy_url: str = ""
    embedding_fingerprint: str = ""
    health: dict[str, Any] = {}


class ModelSettingsResponse(BaseModel):
    default_provider: ProviderSlot
    active_provider: ProviderSlot = "default"
    providers: dict[str, ModelProviderPublic]
    embedding: EmbeddingSettingsPublic


class ModelSettingsUpdateRequest(BaseModel):
    slot: ProviderSlot = "default"
    provider: ModelProviderPayload = ModelProviderPayload()
    embedding: EmbeddingSettingsPayload | None = None
    clear_api_key: bool = False
    clear_embedding_api_key: bool = False
    default_provider: ProviderSlot | None = None


class ModelSettingsTestRequest(BaseModel):
    slot: ProviderSlot = "default"
    provider: ModelProviderPayload | None = None
    embedding: EmbeddingSettingsPayload | None = None


class ModelConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    provider: str
    model: str
    latency_ms: int
    dimensions: int = 0
    index_compatible: bool | None = None
    degrade_reason: str = ""
    embedding_fingerprint: str = ""


class DeveloperSessionResponse(BaseModel):
    required: bool
    unlocked: bool


class DeveloperUnlockRequest(BaseModel):
    pin: str = ""


class MapSettingsResponse(BaseModel):
    provider: MapProvider = "osm"
    baidu_ak: str = ""
    baidu_ak_configured: bool = False
    osm_tile_url: str = ""
    osm_attribution: str = ""
    default_center_lat: float = 0.0
    default_center_lon: float = 0.0
    default_zoom: int = 9


class MapSettingsUpdateRequest(BaseModel):
    provider: MapProvider = "osm"
    baidu_ak: str | None = None
    osm_tile_url: str | None = None
    osm_attribution: str | None = None
    default_center_lat: float | None = None
    default_center_lon: float | None = None
    default_zoom: int | None = None


class MapSettingsTestResponse(BaseModel):
    ok: bool
    message: str
    provider: MapProvider


class HistoryItem(BaseModel):
    id: str
    created_at: str
    request_id: str = ""
    locale: LocaleCode = "zh-CN"
    query_text: str = ""
    gender: Literal["male", "female", "neutral"] = "neutral"
    occasion_text: str = ""
    target_date: str = ""
    confirmed_location_label: str = ""
    location_source: str = ""
    confirmation_mode: str = "smart"
    query_path: str = ""
    headline_advice: str = ""
    weather_summary: str = ""
    selected_coords: SelectedCoords | None = None


class HistoryCreateRequest(BaseModel):
    query_text: str = ""
    gender: Literal["male", "female", "neutral"] = "neutral"
    occasion_text: str = ""
    target_date: str = ""
    confirmed_location_label: str = ""
    location_source: str = ""
    confirmation_mode: str = "smart"
    query_path: str = ""
    headline_advice: str = ""
    weather_summary: str = ""
    selected_coords: SelectedCoords | None = None
    locale: LocaleCode = "zh-CN"
    request_id: str = ""


class FavoriteItem(BaseModel):
    id: str
    label: str
    lat: float
    lon: float
    source: str = ""
    query_text: str = ""
    gender: Literal["male", "female", "neutral"] = "neutral"
    occasion_text: str = ""
    target_date: str = ""
    added_at: str


class FavoriteCreateRequest(BaseModel):
    id: str | None = None
    label: str
    lat: float
    lon: float
    source: str = ""
    query_text: str = ""
    gender: Literal["male", "female", "neutral"] = "neutral"
    occasion_text: str = ""
    target_date: str = ""


class LogSource(BaseModel):
    source: str
    label: str
    kind: str
    size_bytes: int
    updated_at: str


class LogTailResponse(BaseModel):
    source: str
    kind: str
    lines: list[str]
    events: list[dict[str, Any]]
