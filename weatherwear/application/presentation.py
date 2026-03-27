from __future__ import annotations

from typing import Any

from weatherwear.support.common_utils import compact_text
from weatherwear.support.localization import localize_location_label, localize_weather_description


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _msg(locale: str, key: str, **kwargs: Any) -> str:
    messages = {
        "generated_advice": {
            "zh-CN": "结构化穿搭建议已生成。",
            "en-US": "Structured outfit guidance is ready.",
        },
        "no_data": {"zh-CN": "暂无", "en-US": "No data"},
        "none": {"zh-CN": "无", "en-US": "None"},
        "unresolved": {"zh-CN": "未解析成功", "en-US": "Location unresolved"},
        "timezone_unknown": {"zh-CN": "未知时区", "en-US": "Unknown timezone"},
        "map_pin": {"zh-CN": "地图选点", "en-US": "Map pin"},
        "text_search": {"zh-CN": "文本搜索", "en-US": "Text search"},
        "fast_path": {"zh-CN": "快速路径", "en-US": "Fast path"},
        "planner_path": {"zh-CN": "Supervisor 规划", "en-US": "Supervisor plan"},
        "query_success": {"zh-CN": "查询完成", "en-US": "Query complete"},
        "query_waiting": {"zh-CN": "待查询", "en-US": "Waiting for query"},
        "weather_condition": {"zh-CN": "待查询", "en-US": "Waiting for weather"},
        "section_time": {"zh-CN": "分时段建议", "en-US": "Time-of-day plan"},
        "section_layer": {"zh-CN": "上装分层", "en-US": "Upper-body layering"},
        "section_bottoms": {"zh-CN": "下装建议", "en-US": "Bottoms"},
        "section_shoes": {"zh-CN": "鞋子与配饰", "en-US": "Shoes and accessories"},
        "section_notes": {"zh-CN": "结果补充", "en-US": "Extra notes"},
        "badge_weather_mode": {"zh-CN": "天气模式", "en-US": "Weather mode"},
        "badge_confirm_mode": {"zh-CN": "确认模式", "en-US": "Confirmation mode"},
        "badge_location_source": {"zh-CN": "地点来源", "en-US": "Location source"},
        "badge_elapsed": {"zh-CN": "总耗时", "en-US": "Total elapsed"},
        "badge_workflow": {"zh-CN": "工作流", "en-US": "Workflow"},
        "strict_mode": {"zh-CN": "严格确认", "en-US": "Strict confirm"},
        "smart_mode": {"zh-CN": "智能直达", "en-US": "Smart mode"},
        "metric_temp": {"zh-CN": "温度概览", "en-US": "Temperature overview"},
        "metric_feels_like": {"zh-CN": "体感温度", "en-US": "Feels like"},
        "metric_humidity": {"zh-CN": "湿度", "en-US": "Humidity"},
        "metric_wind": {"zh-CN": "风速", "en-US": "Wind"},
        "candidate_confirm_title": {"zh-CN": "确认查询地点", "en-US": "Confirm location candidate"},
        "candidate_confirm_subtitle": {"zh-CN": "请选择你想查询的地点。", "en-US": "Choose the location you want to query."},
        "knowledge_no_match": {
            "zh-CN": "本次未检索到额外经验补充，当前建议主要来自天气信号。",
            "en-US": "No extra outfit note matched this query, so the advice mainly follows the weather signals.",
        },
        "knowledge_matched": {
            "zh-CN": "已命中与当前天气和场景相关的知识依据。",
            "en-US": "Matched outfit notes have been retrieved for this weather and occasion.",
        },
        "knowledge_merged": {
            "zh-CN": "命中的知识依据已合并进本次建议。",
            "en-US": "Matched outfit notes have been merged into this advice.",
        },
        "top_score": {"zh-CN": "综合评分最高", "en-US": "Highest combined score"},
        "source": {"zh-CN": "来源: {source}", "en-US": "Source: {source}"},
        "matched_query": {"zh-CN": "匹配查询: {query}", "en-US": "Matched query: {query}"},
        "with_coords": {"zh-CN": "已带坐标", "en-US": "Coordinates available"},
    }
    locale_key = "en-US" if _is_english(locale) else "zh-CN"
    return messages[key][locale_key].format(**kwargs)


SOURCE_LABELS = {
    "alias_seed": {"zh-CN": "别名种子", "en-US": "Alias seed"},
    "llm_resolution": {"zh-CN": "LLM 候选", "en-US": "LLM candidate"},
    "raw_input": {"zh-CN": "原始输入", "en-US": "Raw input"},
    "direct_geocoding": {"zh-CN": "直接地理编码", "en-US": "Direct geocoding"},
    "geocoding": {"zh-CN": "地理编码", "en-US": "Geocoding"},
    "reverse_geocoding": {"zh-CN": "地图逆地理编码", "en-US": "Reverse geocoding"},
}


def _source_label(locale: str, source: str) -> str:
    values = SOURCE_LABELS.get(source, {})
    return values.get("en-US" if _is_english(locale) else "zh-CN", source or _msg(locale, "no_data"))


def _candidate_reason(locale: str, candidate, index: int) -> str:
    reason_parts = []
    if index == 0:
        reason_parts.append(_msg(locale, "top_score"))
    reason_parts.append(_msg(locale, "source", source=_source_label(locale, candidate.source or "unknown")))
    if candidate.metadata.get("matched_query"):
        reason_parts.append(_msg(locale, "matched_query", query=candidate.metadata["matched_query"]))
    if candidate.lat is not None and candidate.lon is not None:
        reason_parts.append(_msg(locale, "with_coords"))
    return "；".join(reason_parts) if not _is_english(locale) else "; ".join(reason_parts)


def _collect_models(trace: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for record in trace:
        model = str(record.get("model") or "").strip()
        if model and model not in seen:
            seen.append(model)
    return seen


def _condition_emoji(description: str) -> str:
    text = (description or "").lower()
    if "rain" in text or "雨" in text:
        return "🌧️"
    if "snow" in text or "雪" in text:
        return "❄️"
    if "storm" in text or "雷" in text:
        return "⛈️"
    if "cloud" in text or "云" in text:
        return "⛅"
    if "wind" in text or "风" in text:
        return "🌬️"
    if text:
        return "🌤️"
    return "📍"


def _build_fashion_sections(fashion, locale: str) -> list[dict[str, str]]:
    return [
        {"key": "time_of_day", "title": _msg(locale, "section_time"), "content": fashion.time_of_day_advice or ""},
        {"key": "layering", "title": _msg(locale, "section_layer"), "content": fashion.layering_advice or ""},
        {"key": "bottoms", "title": _msg(locale, "section_bottoms"), "content": fashion.bottomwear_advice or ""},
        {"key": "shoes_accessories", "title": _msg(locale, "section_shoes"), "content": fashion.shoes_accessories_advice or ""},
        {"key": "notes", "title": _msg(locale, "section_notes"), "content": fashion.notes_advice or ""},
    ]


def _build_knowledge_basis(fashion, locale: str) -> dict[str, Any]:
    items: list[dict[str, str]] = []
    for hit in getattr(fashion, "knowledge_hits", [])[:3]:
        label = getattr(hit, "label", "") or getattr(hit, "summary", "")
        if not label:
            continue
        items.append(
            {
                "id": getattr(hit, "knowledge_id", ""),
                "label": label,
                "short_reason": getattr(hit, "short_reason", "") or compact_text(getattr(hit, "body", ""), 90),
            }
        )
    status = getattr(fashion, "knowledge_application_mode", "") or ("matched" if items else "no_match")
    if status == "merged":
        summary = _msg(locale, "knowledge_merged")
    elif status == "matched":
        summary = _msg(locale, "knowledge_matched")
    else:
        status = "no_match"
        summary = _msg(locale, "knowledge_no_match")
    return {"status": status, "summary": summary, "items": items}


def _build_decision_factors(result, locale: str) -> list[str]:
    fashion_factors = [str(item).strip() for item in getattr(result.fashion, "dominant_factors", []) if str(item).strip()]
    if fashion_factors:
        return fashion_factors[:3]
    return [str(item).strip() for item in (result.explanation_reasons or []) if str(item).strip()][:3]


def _build_location_pin(result, selected_label: str) -> dict[str, Any]:
    resolution_selected = result.resolution.selected
    lat = None
    lon = None
    label = selected_label
    source = result.location_source
    if resolution_selected and resolution_selected.lat is not None and resolution_selected.lon is not None:
        lat = resolution_selected.lat
        lon = resolution_selected.lon
        source = resolution_selected.source or source
        label = localize_location_label(
            resolution_selected.city,
            resolution_selected.state,
            resolution_selected.country,
            resolution_selected.country_code,
            result.locale,
        ) or selected_label
    elif result.weather.lat is not None and result.weather.lon is not None:
        lat = result.weather.lat
        lon = result.weather.lon
        source = result.weather.source or source
        label = localize_location_label(
            result.weather.city,
            result.weather.state,
            result.weather.country,
            result.weather.country_code,
            result.locale,
        ) or selected_label
    elif result.selected_coords:
        lat = result.selected_coords.get("lat")
        lon = result.selected_coords.get("lon")
    if lat is None or lon is None:
        return {"lat": None, "lon": None, "label": "", "source": source, "confirmed": False, "zoom_hint": 3}
    return {
        "lat": float(lat),
        "lon": float(lon),
        "label": label,
        "source": source,
        "confirmed": result.resolution.resolution_status == "resolved",
        "zoom_hint": 10 if result.location_source == "map_pin" else 8,
    }


def _build_timeline_steps(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, record in enumerate(trace):
        success = bool(record.get("success"))
        steps.append(
            {
                "id": record.get("node_name") or f"step-{index}",
                "title": record.get("name") or record.get("role") or f"Step {index + 1}",
                "role": record.get("role") or "",
                "status": "success" if success else "error",
                "elapsed_ms": int(record.get("elapsed_ms") or 0),
                "cumulative_ms": int(record.get("cumulative_ms") or 0),
                "step_kind": record.get("step_kind") or "",
                "used_llm": bool(record.get("used_llm")),
                "fallback_used": bool(record.get("fallback_used")),
                "provider": record.get("provider") or "",
                "model": record.get("model") or "",
                "decision_reason": record.get("decision_reason") or "",
                "input_summary": record.get("input_summary") or "",
                "output_summary": record.get("output_summary") or "",
                "metadata": record.get("metadata") or {},
                "error": record.get("error") or "",
            }
        )
    return steps


def _build_weather_metrics(weather_view: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    return [
        {
            "key": "temperature_overview",
            "label": _msg(locale, "metric_temp"),
            "value": weather_view.get("temperature", ""),
            "icon": "☁️",
            "tone": "primary",
            "subvalue_left": weather_view.get("temp_min", ""),
            "subvalue_right": weather_view.get("temp_max", ""),
        },
        {
            "key": "feels_like",
            "label": _msg(locale, "metric_feels_like"),
            "value": weather_view.get("feels_like", ""),
            "icon": "🧥",
            "tone": "info",
        },
        {
            "key": "humidity",
            "label": _msg(locale, "metric_humidity"),
            "value": weather_view.get("humidity", ""),
            "icon": "💧",
            "tone": "info",
        },
        {
            "key": "wind",
            "label": _msg(locale, "metric_wind"),
            "value": weather_view.get("wind", ""),
            "icon": "🌬️",
            "tone": "info",
        },
    ]


def _extract_date_portion(value: str | None) -> str:
    text = str(value or "").strip()
    return text[:10] if len(text) >= 10 else ""


def _today_advice_label(locale: str) -> str:
    return "Today's advice" if _is_english(locale) else "今日建议"


def _build_advice_label(
    locale: str,
    *,
    target_date: str | None,
    city_local_time: str | None,
    observed_at_local: str | None,
) -> str:
    requested_date = _extract_date_portion(target_date)
    local_reference_date = _extract_date_portion(city_local_time) or _extract_date_portion(observed_at_local)
    if requested_date and local_reference_date and requested_date != local_reference_date:
        return f"Advice for {requested_date}" if _is_english(locale) else f"{requested_date} 穿搭建议"
    if requested_date and not local_reference_date:
        return f"Advice for {requested_date}" if _is_english(locale) else f"{requested_date} 穿搭建议"
    return _today_advice_label(locale)


def build_result_view_model(
    result,
    recent_queries: list[str] | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    locale = locale or getattr(result, "locale", "zh-CN")
    resolution = result.resolution
    weather = result.weather
    fashion = result.fashion
    trace = [record.to_dict() for record in result.execution_trace]
    selected_label = (
        localize_location_label(
            resolution.selected.city,
            resolution.selected.state,
            resolution.selected.country,
            resolution.selected.country_code,
            locale,
        )
        if resolution.selected
        else _msg(locale, "unresolved")
    )
    models_used = _collect_models(trace)
    total_elapsed_text = f"{result.total_elapsed_ms}ms" if result.total_elapsed_ms else "0ms"
    location_source_label = _msg(locale, "map_pin") if result.location_source == "map_pin" else _msg(locale, "text_search")
    timezone_label = weather.timezone_label or result.timezone_label or _msg(locale, "timezone_unknown")
    localized_condition = localize_weather_description(weather.description, locale)

    weather_view = {
        "ok": weather.ok,
        "city": localize_location_label(weather.city, weather.state, weather.country, weather.country_code, locale),
        "coords": f"{weather.lat}, {weather.lon}" if weather.lat is not None and weather.lon is not None else "",
        "temperature": f"{round(weather.temperature, 1)}{weather.temperature_unit}" if weather.temperature is not None else "",
        "feels_like": f"{round(weather.feels_like, 1)}{weather.temperature_unit}" if weather.feels_like is not None else "",
        "temp_min": f"{round(weather.temp_min, 1)}{weather.temperature_unit}" if weather.temp_min is not None else "",
        "temp_max": f"{round(weather.temp_max, 1)}{weather.temperature_unit}" if weather.temp_max is not None else "",
        "daily_range_text": weather.daily_range_text,
        "description": localized_condition,
        "humidity": f"{weather.humidity}%" if weather.humidity is not None else "",
        "wind": f"{round(weather.wind_speed, 1)} {weather.wind_unit}" if weather.wind_speed is not None else "",
        "source": weather.source,
        "data_mode": weather.data_mode,
        "observed_at": weather.observed_at,
        "observed_at_local": weather.observed_at_local,
        "city_local_time": weather.city_local_time,
        "timezone_label": timezone_label,
        "request_elapsed_ms": weather.request_elapsed_ms,
        "error": weather.error,
        "forecast_date": weather.forecast_date or result.target_date,
        "forecast_mode": weather.forecast_mode or "current",
    }

    knowledge_basis = _build_knowledge_basis(fashion, locale)
    fashion_sections = [section for section in _build_fashion_sections(fashion, locale) if section["content"]]
    decision_factors = _build_decision_factors(result, locale)
    location_pin = _build_location_pin(result, selected_label)
    timeline_steps = _build_timeline_steps(trace)
    headline_advice = fashion.headline_advice or _msg(locale, "generated_advice")
    advice_label = _build_advice_label(
        locale,
        target_date=weather_view["forecast_date"] or result.target_date,
        city_local_time=weather_view["city_local_time"],
        observed_at_local=weather_view["observed_at_local"],
    )
    badges = [
        {"key": "weather_mode", "label": _msg(locale, "badge_weather_mode"), "value": weather.data_mode or "unknown"},
        {
            "key": "confirmation_mode",
            "label": _msg(locale, "badge_confirm_mode"),
            "value": _msg(locale, "strict_mode") if result.confirmation_mode == "strict" else _msg(locale, "smart_mode"),
        },
        {"key": "location_source", "label": _msg(locale, "badge_location_source"), "value": location_source_label},
        {"key": "elapsed", "label": _msg(locale, "badge_elapsed"), "value": total_elapsed_text},
        {"key": "workflow", "label": _msg(locale, "badge_workflow"), "value": result.graph_runtime or _msg(locale, "no_data")},
    ]

    view_model = {
        "summary": {
            "request_id": result.request_id,
            "user_input": result.user_input,
            "plan_intent": result.plan.intent,
            "plan_location": result.plan.raw_location,
            "selected_city": selected_label,
            "resolution_status": resolution.resolution_status,
            "resolution_final_status": result.resolution_final_status or resolution.resolution_status,
            "cached_resolution_status": result.cached_resolution_status,
            "resolution_confidence": resolution.confidence,
            "message": result.message,
            "error": result.error,
            "used_fast_path": result.used_fast_path,
            "graph_runtime": result.graph_runtime,
            "total_elapsed_ms": result.total_elapsed_ms,
            "requested_at": result.requested_at,
            "completed_at": result.completed_at,
            "models_used": models_used,
            "confirmation_mode": result.confirmation_mode,
            "location_source": result.location_source,
            "location_source_label": location_source_label,
            "selected_coords": result.selected_coords,
            "timezone_label": timezone_label,
            "confirmed_location_label": selected_label if resolution.resolution_status == "resolved" else "",
            "locale": locale,
            "retrieval_mode": result.retrieval_mode or "rules_only",
            "vector_leg_status": result.vector_leg_status or "unknown",
            "vector_leg_skipped_reason": result.vector_leg_skipped_reason,
            "fashion_generation_mode": result.fashion_generation_mode or ("llm" if fashion.used_llm else "rule_based"),
            "query_context": {
                "gender": result.gender,
                "occasion_text": result.occasion_text,
                "occasion_tags": list(result.occasion_tags),
                "primary_scene": result.primary_scene,
                "context_tags": list(result.context_tags),
                "target_date": result.target_date or weather.forecast_date or "",
                "forecast_mode": weather.forecast_mode or "current",
            },
        },
        "hero_summary": {
            "title": selected_label,
            "condition": localized_condition or _msg(locale, "weather_condition"),
            "condition_emoji": _condition_emoji(localized_condition),
            "temperature": weather_view["temperature"],
            "feels_like": weather_view["feels_like"],
            "daily_range_text": weather_view["daily_range_text"],
            "advice_label": advice_label,
            "one_line_advice": headline_advice,
            "status_message": result.message or (_msg(locale, "query_success") if result.ok else _msg(locale, "query_waiting")),
            "query_path": _msg(locale, "fast_path") if result.used_fast_path else _msg(locale, "planner_path"),
        },
        "weather": weather_view,
        "weather_metrics": _build_weather_metrics(weather_view, locale),
        "fashion": {
            "text": fashion.advice_text,
            "headline_advice": headline_advice,
            "time_of_day_advice": fashion.time_of_day_advice,
            "layering_advice": fashion.layering_advice,
            "bottomwear_advice": fashion.bottomwear_advice,
            "shoes_accessories_advice": fashion.shoes_accessories_advice,
            "notes_advice": fashion.notes_advice,
            "source": fashion.source,
            "used_llm": fashion.used_llm,
            "error": fashion.error,
        },
        "fashion_sections": fashion_sections,
        "knowledge_basis": knowledge_basis,
        "decision_factors": decision_factors,
        "explanation_reasons": decision_factors,
        "location_pin": location_pin,
        "clarification": {
            "needed": resolution.need_clarification,
            "message": resolution.clarification_message or resolution.failure_reason,
            "recommended_candidate_id": resolution.clarification_candidates[0].candidate_id if resolution.clarification_candidates else "",
            "recommended_label": (
                localize_location_label(
                    resolution.clarification_candidates[0].city,
                    resolution.clarification_candidates[0].state,
                    resolution.clarification_candidates[0].country,
                    resolution.clarification_candidates[0].country_code,
                    locale,
                )
                if resolution.clarification_candidates
                else ""
            ),
            "current_selection_label": selected_label if resolution.selected else "",
            "options": [],
        },
        "clarification_panel": {},
        "trace": trace,
        "timeline_steps": timeline_steps,
        "warnings": result.warnings,
        "dependency_status": result.dependency_status,
        "badges": badges,
        "recent_queries": recent_queries or [],
        "metrics_snapshot": result.metrics_snapshot,
        "bottomwear_section": {
            "title": _msg(locale, "section_bottoms"),
            "content": fashion.bottomwear_advice,
        },
        "debug_sections": {
            "runtime_summary": {
                "request_id": result.request_id,
                "resolution_final_status": result.resolution_final_status or resolution.resolution_status,
                "cached_resolution_status": result.cached_resolution_status,
                "weather_data_mode": weather.data_mode,
                "retrieval_mode": result.retrieval_mode or "rules_only",
                "vector_leg_status": result.vector_leg_status or "unknown",
                "vector_leg_skipped_reason": result.vector_leg_skipped_reason,
                "fashion_generation_mode": result.fashion_generation_mode or ("llm" if fashion.used_llm else "rule_based"),
            },
            "retrieval_summary": {
                "rule_hits": len(
                    next(
                        (
                            (step.get("metadata") or {}).get("hits", [])
                            for step in timeline_steps
                            if step.get("id") == "retrieve_knowledge_rules"
                        ),
                        [],
                    )
                ),
                "vector_hits": len(
                    next(
                        (
                            (step.get("metadata") or {}).get("hits", [])
                            for step in timeline_steps
                            if step.get("id") == "retrieve_knowledge_vector"
                        ),
                        [],
                    )
                ),
                "selected_knowledge_ids": [hit.knowledge_id for hit in getattr(fashion, "knowledge_hits", [])],
                "vector_leg_skipped_reason": result.vector_leg_skipped_reason,
            },
            "warnings": result.warnings,
            "metrics": result.metrics_snapshot,
            "dependency_status": result.dependency_status,
            "knowledge": [hit.to_dict() for hit in getattr(fashion, "knowledge_hits", [])],
            "trace_text": "\n".join(
                f"- {step['title']} | status={step['status']} | model={step['model'] or _msg(locale, 'none')} | provider={step['provider'] or _msg(locale, 'none')}"
                for step in timeline_steps
            ),
        },
    }

    for index, candidate in enumerate(resolution.clarification_candidates):
        view_model["clarification"]["options"].append(
            {
                "candidate_id": candidate.candidate_id,
                "label": localize_location_label(candidate.city, candidate.state, candidate.country, candidate.country_code, locale) or candidate.display_name,
                "confidence": candidate.confidence,
                "source": _source_label(locale, candidate.source or "unknown"),
                "coords": f"{candidate.lat}, {candidate.lon}" if candidate.lat is not None and candidate.lon is not None else "",
                "reason": _candidate_reason(locale, candidate, index),
                "recommended": index == 0,
            }
        )

    if view_model["clarification"]["options"]:
        view_model["clarification_panel"] = {
            "title": _msg(locale, "candidate_confirm_title"),
            "subtitle": resolution.clarification_message or _msg(locale, "candidate_confirm_subtitle"),
            "current_selection_label": selected_label if resolution.selected else "",
            "recommended_candidate_id": view_model["clarification"]["recommended_candidate_id"],
            "options": view_model["clarification"]["options"],
        }

    return view_model
