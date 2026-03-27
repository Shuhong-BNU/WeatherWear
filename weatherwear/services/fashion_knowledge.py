from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from weatherwear.domain.types import ExecutionRecord, KnowledgeHit, WeatherResult
from weatherwear.support.common_utils import compact_text, extract_probable_location, normalize_text, strip_query_noise
from weatherwear.support.llm_support import embed_texts, get_embedding_config, resolve_embedding_runtime_config
from weatherwear.support.runtime_storage import RUNTIME_DIR, read_json, write_json


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "resources" / "fashion_knowledge"
VECTOR_DIR = RUNTIME_DIR / "chroma" / "fashion_knowledge"
MANIFEST_PATH = VECTOR_DIR / "manifest.json"
VECTOR_CACHE_TEMPLATE = "fashion_knowledge_{locale}.vectors.json"
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z-]+|[\u4e00-\u9fff]{2,}")
SUPPORTED_LOCALES = ("zh-CN", "en-US")
VALID_CATEGORIES = {"upper_body", "bottoms", "shoes_accessories", "materials", "occasion"}
ZH_STOP_WORDS = {"今天", "现在", "天气", "穿搭", "建议", "帮我", "帮忙", "查询", "看看"}
EN_STOP_WORDS = {"weather", "outfit", "clothes", "advice", "today", "now", "please", "with", "and", "for", "what"}
PRIMARY_SCENES = {"work", "date", "friends", "home", "exercise", "travel"}
SCENE_PENALTIES = {
    ("friends", "exercise"): 0.35,
    ("friends", "work"): 0.18,
    ("date", "exercise"): 0.30,
    ("work", "exercise"): 0.28,
    ("exercise", "friends"): 0.18,
    ("exercise", "date"): 0.22,
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _msg(locale: str, zh_text: str, en_text: str) -> str:
    return en_text if _is_english(locale) else zh_text


def list_supported_locales() -> list[str]:
    return list(SUPPORTED_LOCALES)


def knowledge_file_for_locale(locale: str) -> Path:
    return KNOWLEDGE_DIR / ("en-US.jsonl" if _is_english(locale) else "zh-CN.jsonl")


def clear_knowledge_caches() -> None:
    _load_knowledge_entries.cache_clear()


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _entry_scene(entry: dict[str, Any]) -> str:
    candidates = [
        str(entry.get("id", "")).strip(),
        " ".join(_normalize_string_list(entry.get("occasion_hints", []))),
        " ".join(_normalize_string_list(entry.get("tags", []))),
        str(entry.get("summary", "")).strip(),
    ]
    normalized = normalize_text(" ".join(item for item in candidates if item))
    for scene in PRIMARY_SCENES:
        if scene and scene in normalized:
            return scene
    return ""


def _occasion_context(entry: dict[str, Any], context: dict[str, Any]) -> tuple[float, list[str], float]:
    score = 0.0
    constraint_bonus = 0.0
    reasons: list[str] = []
    entry_scene = _entry_scene(entry)
    primary_scene = str(context.get("primary_scene", "") or "")
    if primary_scene:
        if entry_scene == primary_scene:
            score += 0.32
            reasons.append(_msg(context["locale"], f"主场景匹配 {primary_scene}", f"Primary scene matched {primary_scene}"))
        elif entry_scene:
            penalty = SCENE_PENALTIES.get((primary_scene, entry_scene), 0.12)
            constraint_bonus -= penalty
            reasons.append(_msg(context["locale"], f"场景降权 {entry_scene}", f"Scene penalty {entry_scene}"))

    context_hits: list[str] = []
    normalized_terms = set(context.get("occasion_keywords", [])) | set(context.get("query_keywords", [])) | {
        normalize_text(tag) for tag in context.get("context_tags", [])
    }
    for keyword in _normalize_string_list(entry.get("occasion_hints", [])):
        normalized = normalize_text(keyword)
        if normalized and normalized in normalized_terms:
            context_hits.append(keyword)
    if context_hits:
        score += min(0.18, 0.06 * len(context_hits))
        reasons.append(
            _msg(
                context["locale"],
                f"场景上下文匹配 {', '.join(context_hits[:3])}",
                f"Context matched {', '.join(context_hits[:3])}",
            )
        )
    return score, reasons[:2], constraint_bonus


@lru_cache(maxsize=4)
def _load_knowledge_entries(locale: str) -> list[dict[str, Any]]:
    path = knowledge_file_for_locale(locale)
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        payload["tags"] = _normalize_string_list(payload.get("tags", []))
        payload["occasion_hints"] = _normalize_string_list(payload.get("occasion_hints", []))
        payload["gender_compatibility"] = _normalize_string_list(payload.get("gender_compatibility", [])) or [
            "neutral",
            "male",
            "female",
        ]
        payload["category"] = str(payload.get("category", "general")).strip() or "general"
        payload["weather_conditions"] = (
            payload.get("weather_conditions", {}) if isinstance(payload.get("weather_conditions"), dict) else {}
        )
        payload["structured_guidance"] = (
            payload.get("structured_guidance", {}) if isinstance(payload.get("structured_guidance"), dict) else {}
        )
        entries.append(payload)
    return entries


def load_knowledge_entries(locale: str, *, refresh: bool = False) -> list[dict[str, Any]]:
    if refresh:
        clear_knowledge_caches()
    return list(_load_knowledge_entries(locale))


def _tokenize_query(query_text: str, locale: str) -> list[str]:
    raw_tokens = TOKEN_PATTERN.findall(strip_query_noise(query_text))
    normalized_location = normalize_text(extract_probable_location(query_text))
    stop_words = EN_STOP_WORDS if _is_english(locale) else ZH_STOP_WORDS
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        normalized = normalize_text(token)
        if not normalized or normalized in stop_words:
            continue
        if normalized_location and normalized in normalized_location:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
    return tokens


def _numeric_value(value: float | int | None, fallback: float = 0.0) -> float:
    return fallback if value is None else float(value)


def _build_query_context(
    weather_result: WeatherResult,
    query_context: dict[str, Any],
    locale: str,
) -> dict[str, Any]:
    query_text = str(query_context.get("query_text", "") or "")
    temperature = (
        _numeric_value(weather_result.temperature, fallback=_numeric_value(weather_result.temp_max, 20.0))
        if weather_result.temperature is not None or weather_result.temp_max is not None
        else 20.0
    )
    feels_like = _numeric_value(weather_result.feels_like, fallback=temperature)
    temp_min = _numeric_value(weather_result.temp_min, fallback=temperature)
    temp_max = _numeric_value(weather_result.temp_max, fallback=temperature)
    gender = str(query_context.get("gender", "neutral") or "neutral").strip() or "neutral"
    occasion_text = str(query_context.get("occasion_text", "") or "")
    occasion_tags = _normalize_string_list(query_context.get("occasion_tags", []))
    primary_scene = str(query_context.get("primary_scene", "") or "")
    context_tags = _normalize_string_list(query_context.get("context_tags", []))
    return {
        "locale": locale,
        "query_text": query_text,
        "query_keywords": _tokenize_query(query_text, locale),
        "occasion_text": occasion_text,
        "occasion_keywords": _tokenize_query(occasion_text, locale),
        "occasion_tags": occasion_tags,
        "primary_scene": primary_scene,
        "context_tags": context_tags,
        "gender": gender,
        "target_date": str(query_context.get("target_date", "") or ""),
        "condition": weather_result.description or "",
        "condition_normalized": normalize_text(weather_result.description),
        "temperature": temperature,
        "feels_like": feels_like,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "temp_range": round(max(temp_max - temp_min, 0.0), 1),
        "humidity": _numeric_value(weather_result.humidity),
        "wind_speed": _numeric_value(weather_result.wind_speed),
    }


def _build_document(entry: dict[str, Any]) -> str:
    structured = entry.get("structured_guidance", {})
    return "\n".join(
        filter(
            None,
            [
                str(entry.get("summary", "")).strip(),
                str(entry.get("body", "")).strip(),
                " ".join(_normalize_string_list(entry.get("tags", []))),
                " ".join(_normalize_string_list(entry.get("occasion_hints", []))),
                json.dumps(structured, ensure_ascii=False) if structured else "",
            ],
        )
    )


def _knowledge_hash(locale: str, entries: list[dict[str, Any]]) -> str:
    raw = "\n".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) for entry in entries)
    return hashlib.sha1(f"{locale}\n{raw}".encode("utf-8")).hexdigest()


def _pre_filter_entries(entries: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    gender = context["gender"]
    for entry in entries:
        genders = _normalize_string_list(entry.get("gender_compatibility", []))
        if genders and gender not in genders and "neutral" not in genders:
            continue
        filtered.append(entry)
    primary_scene = str(context.get("primary_scene", "") or "")
    if not primary_scene:
        return filtered
    scene_matches = [entry for entry in filtered if _entry_scene(entry) == primary_scene]
    if len(scene_matches) >= 4:
        return [entry for entry in filtered if not _entry_scene(entry) or _entry_scene(entry) == primary_scene]
    return filtered


def _match_overlap(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    for term in terms:
        normalized = normalize_text(term)
        if normalized and normalized in text:
            hits.append(term)
    return hits


def _score_numeric(value: float, *, minimum: float | None = None, maximum: float | None = None) -> tuple[float, bool]:
    if minimum is not None and value < float(minimum):
        gap = float(minimum) - value
        return max(0.0, 0.08 - gap * 0.02), False
    if maximum is not None and value > float(maximum):
        gap = value - float(maximum)
        return max(0.0, 0.08 - gap * 0.02), False
    if minimum is None and maximum is None:
        return 0.0, True
    return 0.12, True


def _score_rule_entry(entry: dict[str, Any], context: dict[str, Any]) -> tuple[float, list[str], dict[str, float]]:
    conditions = entry.get("weather_conditions", {})
    if not isinstance(conditions, dict):
        conditions = {}
    weather_match_score = 0.0
    occasion_match_score = 0.0
    garment_compatibility = 0.0
    constraint_bonus = 0.0
    reasons: list[str] = []

    for context_key, min_key, max_key, label in [
        ("temperature", "temperature_min", "temperature_max", _msg(context["locale"], "温度", "Temperature")),
        ("feels_like", "feels_like_min", "feels_like_max", _msg(context["locale"], "体感", "Feels-like")),
        ("temp_range", "temp_range_min", "temp_range_max", _msg(context["locale"], "温差", "Range")),
        ("humidity", "humidity_min", "humidity_max", _msg(context["locale"], "湿度", "Humidity")),
        ("wind_speed", "wind_speed_min", "wind_speed_max", _msg(context["locale"], "风速", "Wind")),
    ]:
        part_score, matched = _score_numeric(
            float(context[context_key]),
            minimum=conditions.get(min_key),
            maximum=conditions.get(max_key),
        )
        weather_match_score += part_score
        if matched and (min_key in conditions or max_key in conditions):
            reasons.append(f"{label} matched")

    condition_hits = _match_overlap(
        str(context["condition_normalized"]),
        _normalize_string_list(conditions.get("condition_any", [])),
    )
    if condition_hits:
        weather_match_score += 0.22
        reasons.append(
            _msg(
                context["locale"],
                f"天气条件匹配 {', '.join(condition_hits)}",
                f"Condition matched {', '.join(condition_hits)}",
            )
        )

    occasion_score, occasion_reasons, scene_constraint = _occasion_context(entry, context)
    occasion_match_score += occasion_score
    constraint_bonus += scene_constraint
    reasons.extend(occasion_reasons)

    tag_hits: list[str] = []
    query_terms = set(context["query_keywords"]) | set(context["occasion_keywords"]) | {
        normalize_text(tag) for tag in context["occasion_tags"]
    }
    for tag in _normalize_string_list(entry.get("tags", [])):
        if normalize_text(tag) in query_terms:
            tag_hits.append(tag)
    if tag_hits:
        occasion_match_score += min(0.16, 0.04 * len(tag_hits))
        reasons.append(
            _msg(context["locale"], f"标签重合 {', '.join(tag_hits[:3])}", f"Tag overlap {', '.join(tag_hits[:3])}")
        )

    if str(context["gender"]) in _normalize_string_list(entry.get("gender_compatibility", [])):
        garment_compatibility += 0.05
    category = str(entry.get("category", "") or "")
    if category in {"bottoms", "shoes_accessories", "upper_body"}:
        garment_compatibility += 0.04
    if context.get("primary_scene") and _entry_scene(entry) == context.get("primary_scene"):
        garment_compatibility += 0.04

    final_score = max(0.0, weather_match_score + occasion_match_score + garment_compatibility + constraint_bonus)
    return (
        round(final_score, 3),
        reasons[:4],
        {
            "weather_match_score": round(weather_match_score, 3),
            "occasion_match_score": round(occasion_match_score, 3),
            "semantic_similarity": 0.0,
            "garment_compatibility": round(garment_compatibility, 3),
            "constraint_bonus": round(constraint_bonus, 3),
        },
    )


def _rule_hits(entries: list[dict[str, Any]], context: dict[str, Any], limit: int) -> tuple[list[dict[str, Any]], ExecutionRecord]:
    started_at = time.time()
    scored: list[dict[str, Any]] = []
    for entry in entries:
        score, reasons, scoring = _score_rule_entry(entry, context)
        if score <= 0:
            continue
        scored.append({"entry": entry, "score": score, "reasons": reasons, "source": "rules", "scoring": scoring})
    scored.sort(key=lambda item: (-item["score"], str(item["entry"].get("id", ""))))
    record = ExecutionRecord(
        role=_msg(context["locale"], "知识规则检索", "Knowledge rule retrieval"),
        name="FashionKnowledgeRules",
        node_name="retrieve_knowledge_rules",
        step_kind="rule_retrieval",
        provider="local_jsonl",
        success=True,
        used_llm=False,
        fallback_used=False,
        elapsed_ms=int((time.time() - started_at) * 1000),
        input_summary=compact_text(
            json.dumps(
                {
                    "occasion_tags": context["occasion_tags"],
                    "primary_scene": context.get("primary_scene", ""),
                    "gender": context["gender"],
                    "condition": context["condition"],
                },
                ensure_ascii=False,
            ),
            max_len=160,
        ),
        output_summary=compact_text(
            json.dumps([{"id": item["entry"].get("id", ""), "score": item["score"]} for item in scored[:limit]], ensure_ascii=False),
            max_len=160,
        ),
        metadata={
            "primary_scene": context.get("primary_scene", ""),
            "context_tags": list(context.get("context_tags", [])),
            "hits": [
                {
                    "id": item["entry"].get("id", ""),
                    "score": item["score"],
                    "reasons": item["reasons"],
                    "scoring": item.get("scoring", {}),
                }
                for item in scored[:limit]
            ],
        },
    )
    return scored[:limit], record


def _load_manifest() -> dict[str, Any]:
    return read_json(MANIFEST_PATH, {})


def _save_manifest(payload: dict[str, Any]) -> None:
    write_json(MANIFEST_PATH, payload)


def _vector_cache_path(locale: str) -> Path:
    return VECTOR_DIR / VECTOR_CACHE_TEMPLATE.format(locale=locale.replace("-", "_").lower())


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(len(left)))
    return max(0.0, dot / (left_norm * right_norm))


def _current_embedding_identity() -> dict[str, Any]:
    config = resolve_embedding_runtime_config()
    return {
        "provider": str(config.get("runtime_provider", "") or ""),
        "base_url": str(config.get("runtime_base_url", "") or ""),
        "model": str(config.get("model", "") or ""),
        "embedding_fingerprint": str(config.get("embedding_fingerprint", "") or ""),
    }


def _index_metadata_from_embedding(info: dict[str, Any], *, version: str, count: int) -> dict[str, Any]:
    identity = _current_embedding_identity()
    return {
        "knowledge_version": version,
        "count": count,
        "embedding_provider": str(info.get("provider", identity["provider"]) or identity["provider"]),
        "embedding_model": str(info.get("model", identity["model"]) or identity["model"]),
        "embedding_base_url": identity["base_url"],
        "embedding_dim": int(info.get("dimensions", 0) or 0),
        "embedding_fingerprint": str(
            info.get("embedding_fingerprint", identity["embedding_fingerprint"]) or identity["embedding_fingerprint"]
        ),
        "built_at": _utc_now_iso(),
    }


def _index_identity_matches(metadata: dict[str, Any]) -> bool:
    identity = _current_embedding_identity()
    return (
        str(metadata.get("embedding_provider", "") or "") == identity["provider"]
        and str(metadata.get("embedding_model", "") or "") == identity["model"]
        and str(metadata.get("embedding_base_url", "") or "") == identity["base_url"]
    )


def get_vector_index_status(locales: list[str] | None = None) -> dict[str, Any]:
    locales = locales or list_supported_locales()
    cache_status: dict[str, Any] = {}
    overall: bool | None = None
    for locale in locales:
        cache_path = _vector_cache_path(locale)
        payload = read_json(cache_path, {})
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        compatible = None
        if metadata:
            compatible = _index_identity_matches(metadata)
        cache_status[locale] = {
            "present": bool(metadata),
            "path": str(cache_path),
            "metadata": metadata,
            "compatible": compatible,
        }
        if compatible is False:
            overall = False
        elif compatible is True and overall is None:
            overall = True
    manifest = _load_manifest()
    return {
        "index_compatible": overall,
        "cache": cache_status,
        "manifest": manifest if isinstance(manifest, dict) else {},
    }


def _ensure_vector_cache(locale: str, entries: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    embedding_config = get_embedding_config()
    if not embedding_config.get("enabled"):
        return None, {"ok": False, "error": "embedding_disabled", "fallback_used": True}

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    version = _knowledge_hash(locale, entries)
    cache_path = _vector_cache_path(locale)
    cached = read_json(cache_path, {})
    cached_metadata = cached.get("metadata", {}) if isinstance(cached, dict) else {}
    if isinstance(cached, dict) and cached.get("version") == version and isinstance(cached.get("items"), list):
        if cached_metadata and not _index_identity_matches(cached_metadata):
            return None, {"ok": False, "error": "index_embedding_mismatch", "fallback_used": True, "index": cached_metadata}
        return cached, {"ok": True, "rebuilt": False, "provider": "json_vector_cache", "index": cached_metadata}

    documents = [_build_document(entry) for entry in entries]
    vectors, info = embed_texts(documents)
    if not info.get("ok") or not vectors:
        return None, info

    metadata = _index_metadata_from_embedding(info, version=version, count=len(entries))
    payload = {
        "version": version,
        "metadata": metadata,
        "items": [{"id": str(entry.get("id", "")), "embedding": vector} for entry, vector in zip(entries, vectors, strict=False)],
    }
    write_json(cache_path, payload)
    return payload, {"ok": True, "rebuilt": True, "provider": "json_vector_cache", "index": metadata}


def _ensure_vector_collection(locale: str, entries: list[dict[str, Any]]) -> tuple[Any | None, dict[str, Any]]:
    embedding_config = get_embedding_config()
    if not embedding_config.get("enabled"):
        return None, {"ok": False, "error": "embedding_disabled", "fallback_used": True}

    try:
        import chromadb
    except Exception as exc:
        return None, {"ok": False, "error": f"chromadb_missing:{exc}", "fallback_used": True}

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    collection_name = f"fashion_knowledge_{locale.replace('-', '_').lower()}"
    manifest = _load_manifest()
    version = _knowledge_hash(locale, entries)
    locale_manifest = manifest.get(locale, {}) if isinstance(manifest, dict) else {}
    if locale_manifest and locale_manifest.get("knowledge_version") == version and not _index_identity_matches(locale_manifest):
        return None, {"ok": False, "error": "index_embedding_mismatch", "fallback_used": True, "index": locale_manifest}

    try:
        client = chromadb.PersistentClient(path=str(VECTOR_DIR))
    except Exception as exc:
        return None, {"ok": False, "error": f"chromadb_client_failed:{exc}", "fallback_used": True}

    rebuild_required = locale_manifest.get("knowledge_version") != version
    if rebuild_required:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(collection_name, metadata={"locale": locale, "version": version})
        documents = [_build_document(entry) for entry in entries]
        vectors, info = embed_texts(documents)
        if not info.get("ok") or not vectors:
            return None, info
        collection.add(
            ids=[str(entry.get("id", "")) for entry in entries],
            documents=documents,
            embeddings=vectors,
            metadatas=[
                {
                    "locale": locale,
                    "category": str(entry.get("category", "general")),
                    "tags": ",".join(_normalize_string_list(entry.get("tags", []))),
                }
                for entry in entries
            ],
        )
        metadata = _index_metadata_from_embedding(info, version=version, count=len(entries))
        manifest[locale] = metadata
        _save_manifest(manifest)
        return collection, {"ok": True, "rebuilt": True, "provider": "chroma", "index": metadata}

    collection = client.get_or_create_collection(collection_name)
    return collection, {"ok": True, "rebuilt": False, "provider": "chroma", "index": locale_manifest}


def rebuild_vector_indexes(locales: list[str] | None = None, *, force: bool = False) -> dict[str, Any]:
    locales = locales or list_supported_locales()
    manifest = _load_manifest()
    if not isinstance(manifest, dict):
        manifest = {}

    if force:
        for locale in locales:
            cache_path = _vector_cache_path(locale)
            if cache_path.exists():
                cache_path.unlink(missing_ok=True)
            manifest.pop(locale, None)
        _save_manifest(manifest)

    results: dict[str, Any] = {}
    for locale in locales:
        entries = load_knowledge_entries(locale, refresh=True)
        cache_payload, cache_info = _ensure_vector_cache(locale, entries)
        collection, chroma_info = _ensure_vector_collection(locale, entries)
        results[locale] = {
            "knowledge_file": str(knowledge_file_for_locale(locale)),
            "entry_count": len(entries),
            "cache": {
                **cache_info,
                "path": str(_vector_cache_path(locale)),
                "present": bool(cache_payload),
            },
            "chroma": {
                **chroma_info,
                "present": collection is not None,
            },
        }
    return {
        "ok": True,
        "locales": results,
        "index_status": get_vector_index_status(locales),
    }


def _vector_failure_record(
    context: dict[str, Any],
    error: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], ExecutionRecord]:
    meta = dict(metadata or {})
    meta.update(
        {
            "vector_leg_status": "skipped",
            "vector_leg_skipped_reason": error,
            "retrieval_mode": "rules_only",
        }
    )
    record = ExecutionRecord(
        role=_msg(context["locale"], "知识向量检索", "Knowledge vector retrieval"),
        name="FashionKnowledgeVector",
        node_name="retrieve_knowledge_vector",
        step_kind="vector_search",
        provider="vector_retrieval",
        success=False,
        used_llm=False,
        fallback_used=True,
        error=error,
        metadata=meta,
    )
    return [], record


def _build_vector_query_text(context: dict[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                context["query_text"],
                context["occasion_text"],
                str(context["condition"]),
                " ".join(context["occasion_tags"]),
                str(context.get("primary_scene", "") or ""),
            ],
        )
    )


def _vector_hits_from_cache(
    entries: list[dict[str, Any]],
    context: dict[str, Any],
    limit: int,
    *,
    error_hint: str = "",
) -> tuple[list[dict[str, Any]], ExecutionRecord]:
    started_at = time.time()
    entry_map = {str(entry.get("id", "")): entry for entry in entries}
    cache_payload, cache_info = _ensure_vector_cache(context["locale"], entries)
    if cache_payload is None:
        return _vector_failure_record(context, str(cache_info.get("error", "vector_cache_failed")), cache_info)

    query_text = _build_vector_query_text(context)
    vectors, embedding_info = embed_texts([query_text])
    if not embedding_info.get("ok") or not vectors:
        return _vector_failure_record(context, str(embedding_info.get("error", "embedding_failed")), embedding_info)

    query_vector = vectors[0]
    cache_metadata = cache_payload.get("metadata", {}) if isinstance(cache_payload, dict) else {}
    if cache_metadata and int(cache_metadata.get("embedding_dim", 0) or 0) not in {0, len(query_vector)}:
        return _vector_failure_record(context, "index_embedding_mismatch", {"index": cache_metadata})

    hits: list[dict[str, Any]] = []
    for item in cache_payload.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", ""))
        entry = entry_map.get(item_id)
        embedding = item.get("embedding")
        if not entry or not isinstance(embedding, list):
            continue
        similarity = _cosine_similarity(query_vector, [float(value) for value in embedding])
        hits.append(
            {
                "entry": entry,
                "score": round(similarity, 3),
                "reasons": [_msg(context["locale"], "向量语义相似", "Semantic similarity match")],
                "source": "vector",
                "scoring": {"semantic_similarity": round(similarity, 3)},
            }
        )
    hits.sort(key=lambda item: (-item["score"], str(item["entry"].get("id", ""))))
    metadata = {
        "hits": [{"id": hit["entry"].get("id", ""), "score": hit["score"]} for hit in hits[:limit]],
        "index": cache_info.get("index", {}),
        "vector_leg_status": "degraded" if error_hint else "healthy",
        "vector_leg_skipped_reason": "",
        "retrieval_mode": "hybrid",
    }
    if error_hint:
        metadata["fallback_reason"] = error_hint
    record = ExecutionRecord(
        role=_msg(context["locale"], "知识向量检索", "Knowledge vector retrieval"),
        name="FashionKnowledgeVector",
        node_name="retrieve_knowledge_vector",
        step_kind="vector_search",
        provider="json_vector_cache",
        success=True,
        used_llm=False,
        fallback_used=bool(error_hint),
        elapsed_ms=int((time.time() - started_at) * 1000),
        input_summary=compact_text(query_text, max_len=160),
        output_summary=compact_text(
            json.dumps([{"id": hit["entry"].get("id", ""), "score": hit["score"]} for hit in hits[:limit]], ensure_ascii=False),
            max_len=160,
        ),
        metadata=metadata,
    )
    return hits[:limit], record


def _vector_hits(entries: list[dict[str, Any]], context: dict[str, Any], limit: int) -> tuple[list[dict[str, Any]], ExecutionRecord]:
    started_at = time.time()
    entry_map = {str(entry.get("id", "")): entry for entry in entries}
    collection, index_info = _ensure_vector_collection(context["locale"], entries)
    if collection is None:
        if str(index_info.get("error", "")).startswith("embedding_disabled"):
            return _vector_failure_record(context, str(index_info.get("error", "vector_disabled")), index_info)
        return _vector_hits_from_cache(entries, context, limit, error_hint=str(index_info.get("error", "")))

    query_text = _build_vector_query_text(context)
    vectors, embedding_info = embed_texts([query_text])
    if not embedding_info.get("ok") or not vectors:
        record = ExecutionRecord(
            role=_msg(context["locale"], "知识向量检索", "Knowledge vector retrieval"),
            name="FashionKnowledgeVector",
            node_name="retrieve_knowledge_vector",
            step_kind="vector_search",
            provider="chroma",
            success=False,
            used_llm=False,
            fallback_used=True,
            error=str(embedding_info.get("error", "embedding_failed")),
            metadata={
                **embedding_info,
                "vector_leg_status": "skipped",
                "vector_leg_skipped_reason": str(embedding_info.get("error", "embedding_failed")),
                "retrieval_mode": "rules_only",
            },
        )
        return [], record

    index_metadata = index_info.get("index", {}) if isinstance(index_info, dict) else {}
    if index_metadata and int(index_metadata.get("embedding_dim", 0) or 0) not in {0, len(vectors[0])}:
        return _vector_failure_record(context, "index_embedding_mismatch", {"index": index_metadata})

    try:
        query_result = collection.query(query_embeddings=vectors, n_results=max(4, limit))
    except Exception as exc:
        return _vector_hits_from_cache(entries, context, limit, error_hint=str(exc))

    ids = (query_result.get("ids") or [[]])[0]
    distances = (query_result.get("distances") or [[]])[0]
    hits: list[dict[str, Any]] = []
    for index, item_id in enumerate(ids):
        entry = entry_map.get(str(item_id))
        if not entry:
            continue
        distance = float(distances[index]) if index < len(distances) else 1.0
        similarity = max(0.0, 1.0 - min(distance, 1.5) / 1.5)
        hits.append(
            {
                "entry": entry,
                "score": round(similarity, 3),
                "reasons": [_msg(context["locale"], "向量语义相似", "Semantic similarity match")],
                "source": "vector",
                "scoring": {"semantic_similarity": round(similarity, 3)},
            }
        )
    record = ExecutionRecord(
        role=_msg(context["locale"], "知识向量检索", "Knowledge vector retrieval"),
        name="FashionKnowledgeVector",
        node_name="retrieve_knowledge_vector",
        step_kind="vector_search",
        provider="chroma",
        success=True,
        used_llm=False,
        fallback_used=False,
        elapsed_ms=int((time.time() - started_at) * 1000),
        input_summary=compact_text(query_text, max_len=160),
        output_summary=compact_text(
            json.dumps([{"id": hit["entry"].get("id", ""), "score": hit["score"]} for hit in hits[:limit]], ensure_ascii=False),
            max_len=160,
        ),
        metadata={
            "hits": [{"id": hit["entry"].get("id", ""), "score": hit["score"]} for hit in hits[:limit]],
            "index": index_info.get("index", {}),
            "vector_leg_status": "healthy",
            "vector_leg_skipped_reason": "",
            "retrieval_mode": "hybrid",
        },
    )
    return hits[:limit], record


def _rerank_hits(
    rule_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    context: dict[str, Any],
    limit: int,
) -> tuple[list[KnowledgeHit], ExecutionRecord]:
    started_at = time.time()
    merged: dict[str, dict[str, Any]] = {}
    for source_hits in (rule_hits, vector_hits):
        for item in source_hits:
            entry = item["entry"]
            item_id = str(entry.get("id", "")).strip()
            current = merged.setdefault(
                item_id,
                {
                    "entry": entry,
                    "rule_score": 0.0,
                    "vector_score": 0.0,
                    "reasons": [],
                    "weather_match_score": 0.0,
                    "occasion_match_score": 0.0,
                    "semantic_similarity": 0.0,
                    "garment_compatibility": 0.0,
                    "constraint_bonus": 0.0,
                },
            )
            if item["source"] == "rules":
                current["rule_score"] = max(current["rule_score"], item["score"])
            else:
                current["vector_score"] = max(current["vector_score"], item["score"])
            scoring = item.get("scoring", {})
            current["weather_match_score"] = max(current["weather_match_score"], float(scoring.get("weather_match_score", 0.0) or 0.0))
            current["occasion_match_score"] = max(current["occasion_match_score"], float(scoring.get("occasion_match_score", 0.0) or 0.0))
            current["semantic_similarity"] = max(current["semantic_similarity"], float(scoring.get("semantic_similarity", 0.0) or 0.0))
            current["garment_compatibility"] = max(
                current["garment_compatibility"],
                float(scoring.get("garment_compatibility", 0.0) or 0.0),
            )
            constraint_bonus = float(scoring.get("constraint_bonus", 0.0) or 0.0)
            current["constraint_bonus"] = (
                min(current["constraint_bonus"], constraint_bonus)
                if constraint_bonus < 0
                else max(current["constraint_bonus"], constraint_bonus)
            )
            current["reasons"] = list(dict.fromkeys(current["reasons"] + item["reasons"]))

    ranked: list[KnowledgeHit] = []
    for item_id, item in merged.items():
        entry = item["entry"]
        coverage_bonus = 0.05 if item["rule_score"] and item["vector_score"] else 0.0
        final_score = max(
            0.0,
            0.30 * item["weather_match_score"]
            + 0.35 * item["occasion_match_score"]
            + 0.15 * item["semantic_similarity"]
            + 0.10 * item["garment_compatibility"]
            + item["constraint_bonus"]
            + coverage_bonus,
        )
        structured = entry.get("structured_guidance", {})
        body = str(entry.get("body", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        short_reason = item["reasons"][0] if item["reasons"] else compact_text(body, 96)
        ranked.append(
            KnowledgeHit(
                knowledge_id=item_id,
                locale=context["locale"],
                label=summary or item_id,
                short_reason=short_reason,
                summary=summary,
                body=body,
                score=round(final_score, 3),
                category=str(entry.get("category", "general") or "general"),
                tags=_normalize_string_list(entry.get("tags", [])),
                match_reasons=item["reasons"][:4] + ([json.dumps(structured, ensure_ascii=False)] if structured else []),
                scoring={
                    "weather_match_score": round(item["weather_match_score"], 3),
                    "occasion_match_score": round(item["occasion_match_score"], 3),
                    "semantic_similarity": round(item["semantic_similarity"], 3),
                    "garment_compatibility": round(item["garment_compatibility"], 3),
                    "constraint_bonus": round(item["constraint_bonus"], 3),
                },
                guidance=structured,
            )
        )

    ranked.sort(key=lambda hit: (-hit.score, hit.knowledge_id))
    final_hits: list[KnowledgeHit] = []
    category_count: dict[str, int] = {}
    for hit in ranked:
        category = hit.category or "general"
        if category_count.get(category, 0) >= 2:
            continue
        final_hits.append(hit)
        category_count[category] = category_count.get(category, 0) + 1
        if len(final_hits) >= limit:
            break
    if len(final_hits) < limit:
        for hit in ranked:
            if hit in final_hits:
                continue
            final_hits.append(hit)
            if len(final_hits) >= limit:
                break

    retrieval_mode = "hybrid" if vector_hits else "rules_only"
    record = ExecutionRecord(
        role=_msg(context["locale"], "知识重排", "Knowledge rerank"),
        name="FashionKnowledgeRerank",
        node_name="rerank_knowledge",
        step_kind="rerank",
        provider="hybrid_retrieval",
        success=True,
        used_llm=False,
        fallback_used=False,
        elapsed_ms=int((time.time() - started_at) * 1000),
        input_summary=compact_text(json.dumps({"rule_hits": len(rule_hits), "vector_hits": len(vector_hits)}, ensure_ascii=False), max_len=120),
        output_summary=compact_text(json.dumps([{"id": hit.knowledge_id, "score": hit.score} for hit in final_hits], ensure_ascii=False), max_len=160),
        metadata={
            "retrieval_mode": retrieval_mode,
            "rule_hit_count": len(rule_hits),
            "vector_hit_count": len(vector_hits),
            "hits": [hit.to_dict() for hit in final_hits],
        },
    )
    return final_hits, record


def retrieve_knowledge_hits(
    weather_result: WeatherResult,
    *,
    locale: str = "zh-CN",
    query_context: dict[str, Any] | None = None,
    limit: int = 5,
    cancel_token: object | None = None,
) -> tuple[list[KnowledgeHit], list[ExecutionRecord]]:
    query_context = query_context or {}
    context = _build_query_context(weather_result, query_context, locale)
    if cancel_token and hasattr(cancel_token, "raise_if_cancelled"):
        cancel_token.raise_if_cancelled("retrieve_knowledge:before")
    entries = _pre_filter_entries(_load_knowledge_entries(locale), context)
    if cancel_token and hasattr(cancel_token, "raise_if_cancelled"):
        cancel_token.raise_if_cancelled("retrieve_knowledge:after_prefilter")
    rule_hits, rule_record = _rule_hits(entries, context, max(5, limit))
    vector_hits, vector_record = _vector_hits(entries, context, max(5, limit))
    final_hits, rerank_record = _rerank_hits(rule_hits, vector_hits, context, max(3, min(limit, 5)))
    rerank_record.metadata["vector_leg_status"] = str(vector_record.metadata.get("vector_leg_status", "unknown") or "unknown")
    rerank_record.metadata["vector_leg_skipped_reason"] = str(
        vector_record.metadata.get("vector_leg_skipped_reason", "") or ""
    )
    return final_hits, [rule_record, vector_record, rerank_record]
