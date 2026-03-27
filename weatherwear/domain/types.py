from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict


@dataclass
class ExecutionRecord:
    role: str
    name: str
    node_name: str = ""
    step_kind: str = ""
    provider: str = ""
    model: str = ""
    input_summary: str = ""
    output_summary: str = ""
    success: bool = False
    used_llm: bool = False
    fallback_used: bool = False
    elapsed_ms: int = 0
    cumulative_ms: int = 0
    error: str = ""
    request_id: str = ""
    decision_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMProviderConfig:
    name: str = "default"
    provider: str = "openai_compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    proxy_url: str = ""
    temperature: float = 0.2
    timeout_seconds: int = 60
    enabled: bool = False
    missing_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRegistry:
    default_provider: str = "default"
    providers: dict[str, LLMProviderConfig] = field(default_factory=dict)
    embedding: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_provider": self.default_provider,
            "providers": {name: config.to_dict() for name, config in self.providers.items()},
            "embedding": dict(self.embedding),
        }


@dataclass
class LocationCandidate:
    candidate_id: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    country_code: str = ""
    lat: float | None = None
    lon: float | None = None
    confidence: float = 0.0
    source: str = "unknown"
    query_text: str = ""
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CityResolutionResult:
    raw_input: str
    normalized_input: str
    resolution_status: str = "pending"
    llm_candidates: list[LocationCandidate] = field(default_factory=list)
    validated_candidates: list[LocationCandidate] = field(default_factory=list)
    clarification_candidates: list[LocationCandidate] = field(default_factory=list)
    selected: LocationCandidate | None = None
    selected_candidate_id: str = ""
    need_clarification: bool = False
    confidence: float = 0.0
    failure_reason: str = ""
    clarification_message: str = ""
    clarification_options: list[str] = field(default_factory=list)
    used_llm: bool = False
    used_alias: bool = False
    fallback_used: bool = False
    execution_records: list[ExecutionRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherResult:
    ok: bool = False
    city: str = ""
    state: str = ""
    country: str = ""
    country_code: str = ""
    lat: float | None = None
    lon: float | None = None
    temperature: float | None = None
    feels_like: float | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    description: str = ""
    humidity: int | None = None
    wind_speed: float | None = None
    temperature_unit: str = "°C"
    wind_unit: str = "m/s"
    observed_at: str = ""
    observed_at_local: str = ""
    city_local_time: str = ""
    timezone_offset: int = 0
    timezone_label: str = ""
    daily_range_text: str = ""
    forecast_date: str = ""
    forecast_mode: str = "current"
    is_forecast: bool = False
    daypart_summaries: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""
    data_mode: str = "unknown"
    demo_mode: bool = False
    fallback_used: bool = False
    request_elapsed_ms: int = 0
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeHit:
    knowledge_id: str = ""
    locale: str = "zh-CN"
    label: str = ""
    short_reason: str = ""
    summary: str = ""
    body: str = ""
    score: float = 0.0
    category: str = ""
    tags: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)
    scoring: dict[str, float] = field(default_factory=dict)
    guidance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FashionAdviceResult:
    advice_text: str = ""
    headline_advice: str = ""
    time_of_day_advice: str = ""
    layering_advice: str = ""
    bottomwear_advice: str = ""
    shoes_accessories_advice: str = ""
    notes_advice: str = ""
    dominant_factors: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)
    optional_refinements: list[str] = field(default_factory=list)
    bottomwear_guidance: list[str] = field(default_factory=list)
    occasion_adjustments: list[str] = field(default_factory=list)
    knowledge_application_mode: str = "no_match"
    used_llm: bool = False
    fallback_used: bool = False
    error: str = ""
    source: str = ""
    knowledge_hits: list[KnowledgeHit] = field(default_factory=list)
    execution_records: list[ExecutionRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryPlan:
    intent: str = "weather_and_fashion"
    raw_location: str = ""
    need_resolution: bool = True
    need_clarification: bool = False
    steps: list[str] = field(default_factory=list)
    fallback_policy: list[str] = field(default_factory=list)
    source: str = "default_safety_plan"
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoordinatorResult:
    ok: bool = False
    request_id: str = ""
    user_input: str = ""
    locale: str = "zh-CN"
    gender: str = "neutral"
    occasion_text: str = ""
    occasion_tags: list[str] = field(default_factory=list)
    primary_scene: str = ""
    context_tags: list[str] = field(default_factory=list)
    target_date: str = ""
    used_fast_path: bool = False
    confirmation_mode: str = "smart"
    location_source: str = "text_search"
    selected_coords: dict[str, float] = field(default_factory=dict)
    graph_runtime: str = ""
    total_elapsed_ms: int = 0
    timezone_label: str = ""
    hero_summary: dict[str, Any] = field(default_factory=dict)
    explanation_reasons: list[str] = field(default_factory=list)
    retrieval_mode: str = "rules_only"
    vector_leg_status: str = "unknown"
    vector_leg_skipped_reason: str = ""
    resolution_final_status: str = ""
    cached_resolution_status: str = ""
    fashion_generation_mode: str = ""
    requested_at: str = ""
    completed_at: str = ""
    plan: QueryPlan = field(default_factory=QueryPlan)
    resolution: CityResolutionResult = field(
        default_factory=lambda: CityResolutionResult(raw_input="", normalized_input="")
    )
    weather: WeatherResult = field(default_factory=WeatherResult)
    fashion: FashionAdviceResult = field(default_factory=FashionAdviceResult)
    execution_trace: list[ExecutionRecord] = field(default_factory=list)
    message: str = ""
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    dependency_status: dict[str, Any] = field(default_factory=dict)
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class QueryState(TypedDict, total=False):
    request_id: str
    locale: str
    gender: str
    occasion_text: str
    occasion_tags: list[str]
    primary_scene: str
    context_tags: list[str]
    target_date: str
    selected_candidate_id: str
    confirmation_mode: str
    location_source: str
    selected_coords: dict[str, float]
    map_reverse_geocode_result: dict[str, Any]
    result: CoordinatorResult
    cancel_token: Any
    plan_record: ExecutionRecord
    started_at: float
    graph_runtime: str
    decision_reason: str
    resolution_step_ok: bool
    weather_step_ok: bool
    fashion_step_ok: bool
