from __future__ import annotations

from typing import Any

from common_utils import compose_location_label


SOURCE_LABELS = {
    "alias_seed": "高频别名",
    "llm_resolution": "LLM 候选",
    "raw_input": "原始输入",
    "direct_geocoding": "直接地理编码",
    "geocoding": "地理编码",
}


def _candidate_reason(candidate, index: int) -> str:
    reason_parts = []
    if index == 0:
        reason_parts.append("综合评分最高")
    source_label = SOURCE_LABELS.get(candidate.source, candidate.source or "未知来源")
    reason_parts.append(f"来源: {source_label}")
    if candidate.metadata.get("matched_query"):
        reason_parts.append(f"匹配查询: {candidate.metadata['matched_query']}")
    if candidate.lat is not None and candidate.lon is not None:
        reason_parts.append("已带定位坐标")
    return "；".join(reason_parts)


def _collect_models(trace: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for record in trace:
        model = str(record.get("model") or "").strip()
        if model and model not in seen:
            seen.append(model)
    return seen


def build_result_view_model(result, recent_queries: list[str] | None = None) -> dict[str, Any]:
    resolution = result.resolution
    weather = result.weather
    fashion = result.fashion
    trace = [record.to_dict() for record in result.execution_trace]
    selected_label = (
        compose_location_label(resolution.selected.city, resolution.selected.state, resolution.selected.country)
        if resolution.selected
        else "未解析成功"
    )
    models_used = _collect_models(trace)
    total_elapsed_text = f"{result.total_elapsed_ms}ms" if result.total_elapsed_ms else "0ms"
    data_time = weather.observed_at_local or weather.observed_at or "未知"

    badges = [
        ("城市解析 LLM", "是" if resolution.used_llm else "否"),
        ("穿衣建议 LLM", "是" if fashion.used_llm else "否"),
        ("发生兜底", "是" if (resolution.fallback_used or weather.fallback_used or fashion.fallback_used) else "否"),
        ("天气模式", weather.data_mode),
        ("使用模型", " / ".join(models_used) if models_used else "未调用"),
        ("总耗时", total_elapsed_text),
        ("工作流运行时", result.graph_runtime or "未知"),
        ("天气数据时间", data_time),
    ]
    view_model = {
        "summary": {
            "request_id": result.request_id,
            "user_input": result.user_input,
            "plan_intent": result.plan.intent,
            "plan_location": result.plan.raw_location,
            "selected_city": selected_label,
            "resolution_status": resolution.resolution_status,
            "resolution_confidence": resolution.confidence,
            "message": result.message,
            "error": result.error,
            "used_fast_path": result.used_fast_path,
            "graph_runtime": result.graph_runtime,
            "total_elapsed_ms": result.total_elapsed_ms,
            "requested_at": result.requested_at,
            "completed_at": result.completed_at,
            "models_used": models_used,
        },
        "weather": {
            "ok": weather.ok,
            "city": compose_location_label(weather.city, weather.state, weather.country),
            "coords": f"{weather.lat}, {weather.lon}" if weather.lat is not None and weather.lon is not None else "",
            "temperature": f"{weather.temperature}{weather.temperature_unit}" if weather.temperature is not None else "",
            "feels_like": f"{weather.feels_like}{weather.temperature_unit}" if weather.feels_like is not None else "",
            "temp_min": f"{weather.temp_min}{weather.temperature_unit}" if weather.temp_min is not None else "",
            "temp_max": f"{weather.temp_max}{weather.temperature_unit}" if weather.temp_max is not None else "",
            "daily_range_text": weather.daily_range_text,
            "description": weather.description,
            "humidity": f"{weather.humidity}%" if weather.humidity is not None else "",
            "wind": f"{weather.wind_speed} {weather.wind_unit}" if weather.wind_speed is not None else "",
            "source": weather.source,
            "data_mode": weather.data_mode,
            "observed_at": weather.observed_at,
            "observed_at_local": weather.observed_at_local,
            "city_local_time": weather.city_local_time,
            "request_elapsed_ms": weather.request_elapsed_ms,
            "error": weather.error,
        },
        "fashion": {
            "text": fashion.advice_text,
            "time_of_day_advice": fashion.time_of_day_advice,
            "layering_advice": fashion.layering_advice,
            "source": fashion.source,
            "used_llm": fashion.used_llm,
            "error": fashion.error,
        },
        "clarification": {
            "needed": resolution.need_clarification,
            "message": resolution.clarification_message or resolution.failure_reason,
            "recommended_candidate_id": (
                resolution.clarification_candidates[0].candidate_id
                if resolution.clarification_candidates
                else ""
            ),
            "recommended_label": (
                resolution.clarification_candidates[0].display_name
                if resolution.clarification_candidates
                else ""
            ),
            "options": [],
        },
        "trace": trace,
        "warnings": result.warnings,
        "dependency_status": result.dependency_status,
        "badges": badges,
        "recent_queries": recent_queries or [],
        "metrics_snapshot": result.metrics_snapshot,
    }

    for index, candidate in enumerate(resolution.clarification_candidates):
        view_model["clarification"]["options"].append(
            {
                "candidate_id": candidate.candidate_id,
                "label": candidate.display_name,
                "confidence": candidate.confidence,
                "source": SOURCE_LABELS.get(candidate.source, candidate.source or "未知来源"),
                "coords": (
                    f"{candidate.lat}, {candidate.lon}"
                    if candidate.lat is not None and candidate.lon is not None
                    else ""
                ),
                "reason": _candidate_reason(candidate, index),
                "recommended": index == 0,
            }
        )

    return view_model
