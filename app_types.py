from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict


@dataclass
class ExecutionRecord:
    role: str
    name: str
    node_name: str = ""
    provider: str = ""
    model: str = ""
    input_summary: str = ""
    output_summary: str = ""
    success: bool = False
    used_llm: bool = False
    fallback_used: bool = False
    elapsed_ms: int = 0
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_provider": self.default_provider,
            "providers": {name: config.to_dict() for name, config in self.providers.items()},
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
    daily_range_text: str = ""
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
class FashionAdviceResult:
    advice_text: str = ""
    time_of_day_advice: str = ""
    layering_advice: str = ""
    used_llm: bool = False
    fallback_used: bool = False
    error: str = ""
    source: str = ""
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
    used_fast_path: bool = False
    graph_runtime: str = ""
    total_elapsed_ms: int = 0
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
    selected_candidate_id: str
    result: CoordinatorResult
    plan_record: ExecutionRecord
    started_at: float
    graph_runtime: str
    decision_reason: str
    resolution_step_ok: bool
    weather_step_ok: bool
    fashion_step_ok: bool
