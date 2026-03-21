from __future__ import annotations

import copy
import threading
import time

from app_types import CityResolutionResult, ExecutionRecord, LocationCandidate
from city_aliases import COMMON_CITY_ALIASES
from common_utils import (
    compose_location_label,
    contains_cjk,
    extract_probable_location,
    has_explicit_region_hint,
    normalize_text,
    stable_id,
    unique_by,
)
from llm_support import extract_json_payload, run_agent


CITY_RESOLVER_SYSTEM_PROMPT = """你是一个全球城市解析助手。
你的唯一任务是把用户输入中的地点，转换成结构化城市候选列表。输出必须是 JSON，不要输出任何解释。
JSON 格式如下：
{
  "candidates": [
    {
      "city": "城市英文名或官方常用名",
      "state": "州/省/地区，没有就留空字符串",
      "country": "国家英文名",
      "country_code": "ISO 两位国家码，未知就留空字符串",
      "confidence": 0.0
    }
  ]
}
规则：
1. 最多返回 3 个候选。
2. 如果用户输入是中文、英文或中英混合地点，都要尽量转成结构化候选。
3. confidence 取值范围是 0 到 1。
4. 不要输出 Markdown。"""

_CACHE: dict[str, tuple[float, CityResolutionResult]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 900


def _cache_key(raw_query: str, fallback_policy: set[str], fast_mode: bool) -> str:
    return "||".join(
        [
            normalize_text(extract_probable_location(raw_query)),
            "fast" if fast_mode else "full",
            ",".join(sorted(fallback_policy)),
        ]
    )


def _cache_get(key: str) -> CityResolutionResult | None:
    with _CACHE_LOCK:
        record = _CACHE.get(key)
        if not record:
            return None
        expires_at, payload = record
        if expires_at < time.time():
            _CACHE.pop(key, None)
            return None
        return copy.deepcopy(payload)


def _cache_set(key: str, payload: CityResolutionResult):
    snapshot = copy.deepcopy(payload)
    snapshot.execution_records = []
    with _CACHE_LOCK:
        _CACHE[key] = (time.time() + _CACHE_TTL_SECONDS, snapshot)


def _candidate_from_seed(seed: dict[str, object], raw_query: str, source: str, confidence: float) -> LocationCandidate:
    city = str(seed.get("city", ""))
    state = str(seed.get("state", ""))
    country = str(seed.get("country", ""))
    country_code = str(seed.get("country_code", ""))
    lat = seed.get("lat")
    lon = seed.get("lon")
    display_name = compose_location_label(city, state, country)
    return LocationCandidate(
        candidate_id=stable_id(city, state, country_code, str(lat), str(lon)),
        city=city,
        state=state,
        country=country,
        country_code=country_code,
        lat=lat,
        lon=lon,
        confidence=confidence,
        source=source,
        query_text=raw_query,
        display_name=display_name,
        metadata={"seed_source": source},
    )


def _parse_llm_candidates(raw_query: str, llm_text: str) -> list[LocationCandidate]:
    payload = extract_json_payload(llm_text)
    if not payload:
        return []

    if isinstance(payload, dict):
        raw_candidates = payload.get("candidates", [])
    elif isinstance(payload, list):
        raw_candidates = payload
    else:
        raw_candidates = []

    candidates: list[LocationCandidate] = []
    for index, item in enumerate(raw_candidates[:3]):
        if not isinstance(item, dict):
            continue
        city = str(item.get("city", "")).strip()
        if not city:
            continue
        state = str(item.get("state", "")).strip()
        country = str(item.get("country", "")).strip()
        country_code = str(item.get("country_code", "")).strip()
        try:
            confidence = float(item.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        display_name = compose_location_label(city, state, country or country_code)
        candidates.append(
            LocationCandidate(
                candidate_id=stable_id(city, state, country_code or country, str(index), raw_query),
                city=city,
                state=state,
                country=country,
                country_code=country_code,
                confidence=max(0.0, min(1.0, confidence)),
                source="llm_resolution",
                query_text=raw_query,
                display_name=display_name,
                metadata={"llm_rank": index},
            )
        )
    return candidates


def _lookup_alias(normalized_query: str) -> dict[str, object] | None:
    if not normalized_query:
        return None
    if normalized_query in COMMON_CITY_ALIASES:
        return COMMON_CITY_ALIASES[normalized_query]

    best_match = None
    best_key_length = -1
    for key, value in COMMON_CITY_ALIASES.items():
        if key and key in normalized_query and len(key) > best_key_length:
            best_match = value
            best_key_length = len(key)
    return best_match


def _find_by_candidate_id(candidates: list[LocationCandidate], candidate_id: str) -> LocationCandidate | None:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    return None


def _mark_clarification(result: CityResolutionResult, candidates: list[LocationCandidate], message: str):
    result.need_clarification = True
    result.resolution_status = "needs_clarification"
    result.clarification_message = message
    result.clarification_candidates = candidates[:5]
    result.clarification_options = [candidate.display_name for candidate in result.clarification_candidates]


def _choose_best_candidate(result: CityResolutionResult, preferred_candidate_id: str = "") -> CityResolutionResult:
    candidates = sorted(result.validated_candidates, key=lambda item: item.confidence, reverse=True)
    if not candidates:
        result.failure_reason = "没有找到可验证的城市候选。"
        result.need_clarification = False
        result.resolution_status = "failed"
        result.clarification_message = ""
        return result

    if preferred_candidate_id:
        selected = _find_by_candidate_id(candidates, preferred_candidate_id)
        if selected:
            result.selected = selected
            result.selected_candidate_id = selected.candidate_id
            result.confidence = selected.confidence
            result.resolution_status = "resolved"
            result.need_clarification = False
            return result

    if result.used_alias:
        alias_candidate = next((item for item in candidates if item.source == "alias_seed"), None)
        if alias_candidate and alias_candidate.confidence >= 0.72:
            result.selected = alias_candidate
            result.selected_candidate_id = alias_candidate.candidate_id
            result.confidence = alias_candidate.confidence
            result.resolution_status = "resolved"
            result.need_clarification = False
            return result

    top = candidates[0]
    result.confidence = top.confidence
    if len(candidates) > 1:
        top_group = [
            candidate
            for candidate in candidates
            if normalize_text(candidate.city) == normalize_text(top.city)
        ]
        second = candidates[1]
        same_city_ambiguous = len(top_group) > 1 and not has_explicit_region_hint(result.normalized_input)
        if same_city_ambiguous and (top.confidence - second.confidence) <= 0.14:
            _mark_clarification(result, top_group, "检测到多个同名城市候选，请确认你想查询的是哪一个。")
            return result
        if not has_explicit_region_hint(result.normalized_input) and (top.confidence - second.confidence) <= 0.08:
            _mark_clarification(result, candidates, "检测到多个接近的城市候选，请确认你想查询的是哪一个。")
            return result

    if top.confidence < 0.58:
        _mark_clarification(result, candidates, "城市匹配置信度偏低，建议补充国家、州省或更完整的地名。")
        return result

    result.selected = top
    result.selected_candidate_id = top.candidate_id
    result.resolution_status = "resolved"
    result.need_clarification = False
    return result


def _unique_validated_candidates(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
    return unique_by(
        sorted(candidates, key=lambda item: item.confidence, reverse=True),
        lambda item: (
            round(item.lat or 0.0, 4),
            round(item.lon or 0.0, 4),
            normalize_text(item.city),
            normalize_text(item.state),
            normalize_text(item.country_code or item.country),
        ),
    )


def _build_cache_record(normalized_input: str, resolution_status: str) -> ExecutionRecord:
    return ExecutionRecord(
        role="城市解析缓存",
        name="ResolutionCache",
        node_name="resolve_city",
        provider="memory_cache",
        input_summary=normalized_input,
        output_summary=resolution_status,
        success=resolution_status in {"resolved", "needs_clarification"},
        used_llm=False,
        fallback_used=False,
        metadata={"cache_hit": True},
    )


def _attempt_fast_resolution(
    result: CityResolutionResult,
    weather_service,
    normalized_input: str,
    fallback_policy: set[str],
    preferred_candidate_id: str,
) -> CityResolutionResult:
    seed_candidates: list[LocationCandidate] = []
    if "alias_lookup" in fallback_policy:
        alias_seed = _lookup_alias(normalize_text(normalized_input))
        if alias_seed:
            result.used_alias = True
            seed_candidates.append(_candidate_from_seed(alias_seed, normalized_input, "alias_seed", 0.97))

    validated_candidates: list[LocationCandidate] = []
    for candidate in seed_candidates:
        validated_candidates.extend(weather_service.validate_candidate(candidate))

    if "direct_geocoding" in fallback_policy:
        direct_hits = weather_service.geocode_city(normalized_input, limit=6)
        for candidate in direct_hits:
            candidate.source = "direct_geocoding"
        validated_candidates.extend(direct_hits)
        if direct_hits:
            result.fallback_used = True

    result.validated_candidates = _unique_validated_candidates(validated_candidates)
    return _choose_best_candidate(result, preferred_candidate_id=preferred_candidate_id)


def resolve_city(
    raw_query: str,
    weather_service,
    *,
    fallback_policy: set[str] | None = None,
    preferred_candidate_id: str = "",
    fast_mode: bool = False,
) -> CityResolutionResult:
    normalized_input = extract_probable_location(raw_query)
    result = CityResolutionResult(
        raw_input=raw_query,
        normalized_input=normalized_input,
        resolution_status="pending",
    )
    fallback_policy = fallback_policy or {"alias_lookup", "llm_city_resolution", "direct_geocoding"}
    cache_key = _cache_key(raw_query, fallback_policy, fast_mode)

    cached = _cache_get(cache_key)
    if cached is not None:
        cached.execution_records.append(_build_cache_record(normalized_input, cached.resolution_status))
        if preferred_candidate_id:
            cached.need_clarification = False
            cached.clarification_message = ""
            cached = _choose_best_candidate(cached, preferred_candidate_id=preferred_candidate_id)
        return cached

    if fast_mode:
        fast_result = _attempt_fast_resolution(
            result,
            weather_service,
            normalized_input,
            fallback_policy,
            preferred_candidate_id,
        )
        if fast_result.resolution_status in {"resolved", "needs_clarification"}:
            _cache_set(cache_key, fast_result)
            return copy.deepcopy(fast_result)

    seed_candidates: list[LocationCandidate] = []
    if "alias_lookup" in fallback_policy:
        alias_seed = _lookup_alias(normalize_text(normalized_input))
        if alias_seed:
            result.used_alias = True
            seed_candidates.append(_candidate_from_seed(alias_seed, normalized_input, "alias_seed", 0.97))

    llm_candidates: list[LocationCandidate] = []
    should_use_llm = "llm_city_resolution" in fallback_policy and (
        contains_cjk(normalized_input) or not seed_candidates or len(normalized_input.split()) > 1 or not fast_mode
    )
    if should_use_llm:
        prompt = (
            "请把下面的地点输入解析成最多 3 个结构化城市候选，只输出 JSON。\n"
            f"用户输入: {normalized_input}"
        )
        llm_text, record = run_agent(
            role="城市解析智能体",
            name="CityResolverAgent",
            system_prompt=CITY_RESOLVER_SYSTEM_PROMPT,
            prompt=prompt,
            json_mode=True,
        )
        record.node_name = "resolve_city"
        record.decision_reason = "normalize_location_candidates"
        result.execution_records.append(record)
        llm_candidates = _parse_llm_candidates(normalized_input, llm_text)
        result.used_llm = record.used_llm and bool(llm_candidates)
        if record.fallback_used:
            result.fallback_used = True
    result.llm_candidates = llm_candidates

    direct_candidate = LocationCandidate(
        candidate_id=stable_id(normalized_input, "", "", "", raw_query),
        city=normalized_input,
        confidence=0.42,
        source="raw_input",
        query_text=normalized_input,
        display_name=normalized_input,
        metadata={"seed_source": "raw_input"},
    )

    merged_candidates = unique_by(
        seed_candidates + llm_candidates + [direct_candidate],
        lambda item: (
            normalize_text(item.city),
            normalize_text(item.state),
            normalize_text(item.country_code or item.country),
            normalize_text(item.query_text),
        ),
    )

    validated_candidates: list[LocationCandidate] = []
    for candidate in merged_candidates:
        validated_candidates.extend(weather_service.validate_candidate(candidate))

    if not validated_candidates and "direct_geocoding" in fallback_policy:
        direct_hits = weather_service.geocode_city(normalized_input, limit=6)
        for candidate in direct_hits:
            candidate.source = "direct_geocoding"
        validated_candidates.extend(direct_hits)
        if direct_hits:
            result.fallback_used = True

    result.validated_candidates = _unique_validated_candidates(validated_candidates)
    final_result = _choose_best_candidate(result, preferred_candidate_id=preferred_candidate_id)
    if final_result.selected:
        final_result.resolution_status = "resolved"
    elif final_result.need_clarification and final_result.resolution_status == "pending":
        final_result.resolution_status = "needs_clarification"
    elif not final_result.need_clarification:
        final_result.resolution_status = "failed"

    _cache_set(cache_key, final_result)
    return copy.deepcopy(final_result)
