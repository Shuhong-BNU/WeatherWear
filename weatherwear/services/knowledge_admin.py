from __future__ import annotations

import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from weatherwear.domain.types import WeatherResult
from weatherwear.services import fashion_knowledge as knowledge


REQUIRED_TEXT_FIELDS = ("id", "locale", "category", "summary", "body")
REQUIRED_LIST_FIELDS = ("tags", "occasion_hints", "gender_compatibility")
KNOWN_WEATHER_NUMERIC_KEYS = {
    "temperature_min",
    "temperature_max",
    "feels_like_min",
    "feels_like_max",
    "temp_range_min",
    "temp_range_max",
    "humidity_min",
    "humidity_max",
    "wind_speed_min",
    "wind_speed_max",
}
KNOWN_WEATHER_LIST_KEYS = {"condition_any"}
KNOWN_WEATHER_KEYS = KNOWN_WEATHER_NUMERIC_KEYS | KNOWN_WEATHER_LIST_KEYS
KNOWN_GENDER_COMPATIBILITY = ("neutral", "male", "female")
FALLBACK_OCCASION_HINTS = {
    "work",
    "date",
    "friends",
    "home",
    "exercise",
    "travel",
    "walking",
    "indoor",
    "outdoor",
    "air_conditioning",
}


def _issue(severity: str, code: str, locale: str, line_number: int, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "locale": locale,
        "line_number": line_number,
        "message": message,
        **extra,
    }


def _read_raw_lines(path: Path) -> list[tuple[int, str]]:
    if not path.exists():
        return []
    rows: list[tuple[int, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if raw.strip():
            rows.append((line_number, raw))
    return rows


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_identifier(value: Any) -> str:
    return _normalize_text(value).lower()


def _normalize_string_list(values: Any, *, lowercase: bool = False) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = _normalize_text(raw)
        if lowercase:
            item = item.lower()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _normalize_guidance_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return _normalize_string_list(value)
    if isinstance(value, str):
        return _normalize_string_list([value])
    return []


def _normalize_weather_conditions(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_text(raw_key)
        if not key:
            continue

        if key == "condition_any":
            conditions = _normalize_string_list(raw_value, lowercase=True)
            if conditions:
                normalized[key] = conditions
            continue

        if key in KNOWN_WEATHER_NUMERIC_KEYS:
            if isinstance(raw_value, (int, float)):
                normalized[key] = raw_value
            continue

        normalized[key] = raw_value

    return normalized


def _normalize_structured_guidance(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_text(raw_key)
        if not key:
            continue
        items = _normalize_guidance_value(raw_value)
        if items:
            normalized[key] = items
    return normalized


def normalize_knowledge_payload(payload: dict[str, Any], *, locale: str | None = None) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["id"] = _normalize_text(payload.get("id"))
    normalized["locale"] = _normalize_text(payload.get("locale")) or _normalize_text(locale)
    normalized["category"] = _normalize_identifier(payload.get("category"))
    normalized["summary"] = _normalize_text(payload.get("summary"))
    normalized["body"] = _normalize_text(payload.get("body"))
    normalized["tags"] = _normalize_string_list(payload.get("tags", []))
    normalized["occasion_hints"] = _normalize_string_list(payload.get("occasion_hints", []), lowercase=True)
    normalized["gender_compatibility"] = _normalize_string_list(payload.get("gender_compatibility", []), lowercase=True)
    normalized["weather_conditions"] = _normalize_weather_conditions(payload.get("weather_conditions", {}))
    normalized["structured_guidance"] = _normalize_structured_guidance(payload.get("structured_guidance", {}))
    return normalized


def normalize_knowledge_payloads(payloads: Iterable[dict[str, Any]], *, locale: str | None = None) -> list[dict[str, Any]]:
    return [normalize_knowledge_payload(payload, locale=locale) for payload in payloads]


@lru_cache(maxsize=8)
def _load_generated_reference(locale: str) -> dict[str, set[str]]:
    tags: set[str] = set()
    occasion_hints: set[str] = set(FALLBACK_OCCASION_HINTS)

    try:
        from scripts import generate_fashion_knowledge as generated_knowledge

        occasion_hints.update(_normalize_identifier(item.get("id")) for item in generated_knowledge.OCCASIONS)
        for special in generated_knowledge.SPECIALS:
            occasion_hints.update(_normalize_identifier(value) for value in special[3])

        for entry in generated_knowledge.build_locale(locale):
            tags.update(_normalize_text(tag) for tag in entry.get("tags", []))
            occasion_hints.update(_normalize_identifier(value) for value in entry.get("occasion_hints", []))
    except Exception:
        pass

    tags.discard("")
    occasion_hints.discard("")
    return {
        "tags": tags,
        "occasion_hints": occasion_hints,
    }


def _payload_signature(payload: dict[str, Any]) -> str:
    signature_payload = {
        "locale": payload.get("locale"),
        "category": payload.get("category"),
        "summary": payload.get("summary"),
        "body": payload.get("body"),
        "tags": payload.get("tags", []),
        "occasion_hints": payload.get("occasion_hints", []),
        "gender_compatibility": payload.get("gender_compatibility", []),
        "weather_conditions": payload.get("weather_conditions", {}),
        "structured_guidance": payload.get("structured_guidance", {}),
    }
    return json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)


def load_payloads_from_path(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path)
    suffix = resolved.suffix.lower()
    raw = resolved.read_text(encoding="utf-8") if resolved.exists() else ""

    if suffix == ".json":
        payload = json.loads(raw or "[]")
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError(f"Unsupported JSON payload type: {type(payload).__name__}")

    if suffix == ".jsonl":
        payloads: list[dict[str, Any]] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("JSONL entries must be objects.")
            payloads.append(item)
        return payloads

    raise ValueError(f"Unsupported knowledge file format: {resolved.suffix}")


def write_payloads_to_jsonl(path: str | Path, payloads: Iterable[dict[str, Any]]) -> int:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with resolved.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def validate_knowledge_payloads(payloads: list[dict[str, Any]], *, locale: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    normalized_payloads = normalize_knowledge_payloads(payloads, locale=locale)
    seen_ids: dict[str, int] = {}
    category_counter: Counter[str] = Counter()
    summary_body_counter: defaultdict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    signature_counter: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    reference = _load_generated_reference(locale)
    unknown_tag_counter: Counter[str] = Counter()
    unknown_occasion_counter: Counter[str] = Counter()
    normalized_changed_count = 0

    for index, payload in enumerate(normalized_payloads, start=1):
        original = payloads[index - 1]
        if payload != original:
            normalized_changed_count += 1

        entry_id = payload.get("id", "")
        if not entry_id:
            issues.append(_issue("error", "empty_id", locale, index, "Knowledge entry is missing id."))
        elif entry_id in seen_ids:
            issues.append(
                _issue(
                    "error",
                    "duplicate_id",
                    locale,
                    index,
                    f"Knowledge entry id is duplicated: {entry_id}",
                    entry_id=entry_id,
                    first_seen_line=seen_ids[entry_id],
                )
            )
        else:
            seen_ids[entry_id] = index

        for field in REQUIRED_TEXT_FIELDS:
            value = payload.get(field, "")
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    _issue(
                        "error",
                        f"missing_{field}",
                        locale,
                        index,
                        f"Knowledge entry is missing required field: {field}",
                        entry_id=entry_id,
                    )
                )

        payload_locale = payload.get("locale", "")
        if payload_locale and payload_locale != locale:
            issues.append(
                _issue(
                    "error",
                    "locale_mismatch",
                    locale,
                    index,
                    f"Entry locale does not match target locale: {payload_locale}",
                    entry_id=entry_id,
                )
            )

        category = payload.get("category", "")
        if category:
            category_counter[category] += 1
        if category and category not in knowledge.VALID_CATEGORIES:
            issues.append(
                _issue(
                    "error",
                    "invalid_category",
                    locale,
                    index,
                    f"Invalid category: {category}",
                    entry_id=entry_id,
                    category=category,
                )
            )

        tags = payload.get("tags", [])
        if not isinstance(original.get("tags", []), list):
            issues.append(_issue("error", "invalid_tags", locale, index, "tags must be a list.", entry_id=entry_id))
            tags = []
        elif len(tags) < len([item for item in original.get("tags", []) if _normalize_text(item)]):
            issues.append(_issue("warning", "duplicate_tags", locale, index, "tags contains duplicate or blank items.", entry_id=entry_id))

        for tag in tags:
            if reference["tags"] and tag not in reference["tags"]:
                unknown_tag_counter[tag] += 1

        occasion_hints = payload.get("occasion_hints", [])
        if not isinstance(original.get("occasion_hints", []), list):
            issues.append(
                _issue("error", "invalid_occasion_hints", locale, index, "occasion_hints must be a list.", entry_id=entry_id)
            )
            occasion_hints = []
        elif len(occasion_hints) < len([item for item in original.get("occasion_hints", []) if _normalize_text(item)]):
            issues.append(
                _issue(
                    "warning",
                    "duplicate_occasion_hints",
                    locale,
                    index,
                    "occasion_hints contains duplicate or blank items.",
                    entry_id=entry_id,
                )
            )

        for value in occasion_hints:
            if value not in reference["occasion_hints"]:
                unknown_occasion_counter[value] += 1

        gender_compatibility = payload.get("gender_compatibility", [])
        if not isinstance(original.get("gender_compatibility", []), list):
            issues.append(
                _issue(
                    "error",
                    "invalid_gender_compatibility",
                    locale,
                    index,
                    "gender_compatibility must be a list.",
                    entry_id=entry_id,
                )
            )
            gender_compatibility = []
        elif len(gender_compatibility) < len([item for item in original.get("gender_compatibility", []) if _normalize_text(item)]):
            issues.append(
                _issue(
                    "warning",
                    "duplicate_gender_compatibility",
                    locale,
                    index,
                    "gender_compatibility contains duplicate or blank items.",
                    entry_id=entry_id,
                )
            )

        invalid_genders = [value for value in gender_compatibility if value not in KNOWN_GENDER_COMPATIBILITY]
        if invalid_genders:
            issues.append(
                _issue(
                    "error",
                    "invalid_gender_value",
                    locale,
                    index,
                    f"Unknown gender_compatibility values: {', '.join(invalid_genders)}",
                    entry_id=entry_id,
                    values=invalid_genders,
                )
            )

        weather_conditions = original.get("weather_conditions", {})
        if not isinstance(weather_conditions, dict):
            issues.append(
                _issue(
                    "error",
                    "invalid_weather_conditions",
                    locale,
                    index,
                    "weather_conditions must be an object.",
                    entry_id=entry_id,
                )
            )
        else:
            normalized_weather = payload.get("weather_conditions", {})
            for key in weather_conditions:
                key_name = _normalize_text(key)
                if key_name and key_name not in KNOWN_WEATHER_KEYS:
                    issues.append(
                        _issue(
                            "warning",
                            "unknown_weather_condition_key",
                            locale,
                            index,
                            f"Unknown weather condition key: {key_name}",
                            entry_id=entry_id,
                            key=key_name,
                        )
                    )

            for key in KNOWN_WEATHER_NUMERIC_KEYS:
                if key in weather_conditions and key not in normalized_weather:
                    issues.append(
                        _issue(
                            "error",
                            "invalid_weather_numeric_value",
                            locale,
                            index,
                            f"Weather condition {key} must be numeric.",
                            entry_id=entry_id,
                            key=key,
                        )
                    )

            if "condition_any" in weather_conditions and "condition_any" not in normalized_weather:
                issues.append(
                    _issue(
                        "error",
                        "invalid_condition_any",
                        locale,
                        index,
                        "condition_any must be a non-empty string list.",
                        entry_id=entry_id,
                    )
                )

        structured_guidance = original.get("structured_guidance", {})
        if not isinstance(structured_guidance, dict):
            issues.append(
                _issue(
                    "error",
                    "invalid_structured_guidance",
                    locale,
                    index,
                    "structured_guidance must be an object.",
                    entry_id=entry_id,
                )
            )
        else:
            normalized_guidance = payload.get("structured_guidance", {})
            for raw_key, raw_value in structured_guidance.items():
                key = _normalize_text(raw_key)
                if not key:
                    issues.append(
                        _issue(
                            "warning",
                            "blank_guidance_key",
                            locale,
                            index,
                            "structured_guidance contains a blank key.",
                            entry_id=entry_id,
                        )
                    )
                    continue

                if isinstance(raw_value, list):
                    normalized_value = normalized_guidance.get(key, [])
                    if len(normalized_value) < len([item for item in raw_value if _normalize_text(item)]):
                        issues.append(
                            _issue(
                                "warning",
                                "duplicate_guidance_items",
                                locale,
                                index,
                                f"structured_guidance[{key}] contains duplicate or blank items.",
                                entry_id=entry_id,
                                key=key,
                            )
                        )
                    continue

                if not isinstance(raw_value, str):
                    issues.append(
                        _issue(
                            "error",
                            "invalid_guidance_value",
                            locale,
                            index,
                            f"structured_guidance[{key}] must be a string or string list.",
                            entry_id=entry_id,
                            key=key,
                        )
                    )

        summary = payload.get("summary", "")
        body = payload.get("body", "")
        if summary and body:
            summary_body_counter[(summary, body)].append((index, entry_id))
        signature_counter[_payload_signature(payload)].append((index, entry_id))

    for tag, count in sorted(unknown_tag_counter.items()):
        lines = [index for index, payload in enumerate(normalized_payloads, start=1) if tag in payload.get("tags", [])]
        issues.append(
            _issue(
                "warning",
                "unknown_tag",
                locale,
                lines[0],
                f"Tag is outside the generated reference vocabulary: {tag}",
                tag=tag,
                count=count,
                lines=lines,
            )
        )

    for occasion_hint, count in sorted(unknown_occasion_counter.items()):
        lines = [index for index, payload in enumerate(normalized_payloads, start=1) if occasion_hint in payload.get("occasion_hints", [])]
        issues.append(
            _issue(
                "warning",
                "unknown_occasion_hint",
                locale,
                lines[0],
                f"occasion_hints contains unknown value: {occasion_hint}",
                occasion_hint=occasion_hint,
                count=count,
                lines=lines,
            )
        )

    for (summary, body), matches in summary_body_counter.items():
        if len(matches) < 2:
            continue
        issues.append(
            _issue(
                "warning",
                "duplicate_summary_body",
                locale,
                matches[0][0],
                "Multiple entries share the same summary/body pair.",
                lines=[item[0] for item in matches],
                entry_ids=[item[1] for item in matches],
                summary=summary,
                body=body,
            )
        )

    for signature, matches in signature_counter.items():
        if len(matches) < 2:
            continue
        issues.append(
            _issue(
                "warning",
                "duplicate_entry_signature",
                locale,
                matches[0][0],
                "Multiple entries collapse to the same normalized signature.",
                lines=[item[0] for item in matches],
                entry_ids=[item[1] for item in matches],
                signature=signature,
            )
        )

    return {
        "locale": locale,
        "ok": not any(item["severity"] == "error" for item in issues),
        "entry_count": len(payloads),
        "issues": issues,
        "category_distribution": dict(sorted(category_counter.items())),
        "normalized_changed_count": normalized_changed_count,
        "reference_occasion_hints": sorted(reference["occasion_hints"]),
    }


def _build_alignment_report(payloads_by_locale: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if len(payloads_by_locale) < 2:
        return {"ok": True, "base_locale": None, "pairs": [], "issues": []}

    issues: list[dict[str, Any]] = []
    locales = sorted(payloads_by_locale)
    base_locale = "en-US" if "en-US" in payloads_by_locale else locales[0]
    base_entries = {entry.get("id", ""): entry for entry in normalize_knowledge_payloads(payloads_by_locale[base_locale], locale=base_locale)}
    pairs: list[dict[str, Any]] = []

    for locale in locales:
        if locale == base_locale:
            continue

        compared_entries = {entry.get("id", ""): entry for entry in normalize_knowledge_payloads(payloads_by_locale[locale], locale=locale)}
        base_ids = {entry_id for entry_id in base_entries if entry_id}
        compared_ids = {entry_id for entry_id in compared_entries if entry_id}
        missing_ids = sorted(base_ids - compared_ids)
        extra_ids = sorted(compared_ids - base_ids)
        category_mismatches: list[dict[str, str]] = []

        for entry_id in sorted(base_ids & compared_ids):
            base_category = str(base_entries[entry_id].get("category", ""))
            compared_category = str(compared_entries[entry_id].get("category", ""))
            if base_category != compared_category:
                category_mismatches.append(
                    {
                        "id": entry_id,
                        "base_category": base_category,
                        "locale_category": compared_category,
                    }
                )

        if missing_ids:
            issues.append(
                _issue(
                    "warning",
                    "cross_locale_missing_ids",
                    locale,
                    0,
                    f"{locale} is missing {len(missing_ids)} ids compared with {base_locale}.",
                    base_locale=base_locale,
                    missing_ids=missing_ids,
                )
            )
        if extra_ids:
            issues.append(
                _issue(
                    "warning",
                    "cross_locale_extra_ids",
                    locale,
                    0,
                    f"{locale} has {len(extra_ids)} extra ids compared with {base_locale}.",
                    base_locale=base_locale,
                    extra_ids=extra_ids,
                )
            )
        for mismatch in category_mismatches:
            issues.append(
                _issue(
                    "error",
                    "cross_locale_category_mismatch",
                    locale,
                    0,
                    f"Entry {mismatch['id']} has mismatched category across locales.",
                    base_locale=base_locale,
                    **mismatch,
                )
            )

        pairs.append(
            {
                "locale": locale,
                "base_locale": base_locale,
                "missing_ids": missing_ids,
                "extra_ids": extra_ids,
                "category_mismatches": category_mismatches,
            }
        )

    return {
        "ok": not any(item["severity"] == "error" for item in issues),
        "base_locale": base_locale,
        "pairs": pairs,
        "issues": issues,
    }


def validate_knowledge_base(locales: list[str] | None = None) -> dict[str, Any]:
    locales = locales or knowledge.list_supported_locales()
    results: dict[str, Any] = {}
    overall_issues: list[dict[str, Any]] = []
    parsed_payloads_by_locale: dict[str, list[dict[str, Any]]] = {}

    for locale in locales:
        path = knowledge.knowledge_file_for_locale(locale)
        raw_rows = _read_raw_lines(path)
        parsed_payloads: list[dict[str, Any]] = []
        file_issues: list[dict[str, Any]] = []

        for line_number, raw in raw_rows:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                file_issues.append(
                    _issue("error", "invalid_json", locale, line_number, f"JSONL parse failed: {exc.msg}", raw=raw[:160])
                )
                continue
            if not isinstance(payload, dict):
                file_issues.append(_issue("error", "invalid_payload_type", locale, line_number, "Knowledge entry must be an object."))
                continue
            parsed_payloads.append(payload)

        parsed_payloads_by_locale[locale] = parsed_payloads
        validated = validate_knowledge_payloads(parsed_payloads, locale=locale)
        validated["issues"] = file_issues + validated["issues"]
        validated["path"] = str(path)
        validated["raw_line_count"] = len(raw_rows)
        validated["parsed_entry_count"] = len(parsed_payloads)
        validated["ok"] = not any(item["severity"] == "error" for item in validated["issues"])
        results[locale] = validated
        overall_issues.extend(validated["issues"])

    alignment = _build_alignment_report(parsed_payloads_by_locale)
    overall_issues.extend(alignment["issues"])

    return {
        "ok": not any(item["severity"] == "error" for item in overall_issues),
        "locales": results,
        "alignment": alignment,
        "issue_count": len(overall_issues),
    }


def summarize_knowledge_base(locales: list[str] | None = None) -> dict[str, Any]:
    locales = locales or knowledge.list_supported_locales()
    summary: dict[str, Any] = {}
    for locale in locales:
        entries = knowledge.load_knowledge_entries(locale)
        category_distribution = Counter(str(entry.get("category", "general") or "general") for entry in entries)
        tag_distribution = Counter(tag for entry in entries for tag in entry.get("tags", []) if isinstance(tag, str) and tag.strip())
        summary[locale] = {
            "path": str(knowledge.knowledge_file_for_locale(locale)),
            "entry_count": len(entries),
            "categories": dict(sorted(category_distribution.items())),
            "top_tags": dict(tag_distribution.most_common(10)),
        }
    return {"locales": summary}


def default_retrieval_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "cold_work_commute_en",
            "locale": "en-US",
            "weather": {"temperature": 4, "feels_like": 1, "temp_min": 0, "temp_max": 7, "description": "Clear", "humidity": 40, "wind_speed": 4.0},
            "query_context": {
                "query_text": "Beijing outfit advice",
                "occasion_text": "work commute with office AC",
                "occasion_tags": ["work", "office", "air_conditioning"],
                "primary_scene": "work",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["work-cold-upper", "work-cold-bottoms", "work-cold-shoes"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
        {
            "name": "cold_work_commute_zh",
            "locale": "zh-CN",
            "weather": {"temperature": 4, "feels_like": 1, "temp_min": 0, "temp_max": 7, "description": "Clear", "humidity": 40, "wind_speed": 4.0},
            "query_context": {
                "query_text": "北京通勤穿什么",
                "occasion_text": "上班通勤，办公室空调偏冷",
                "occasion_tags": ["work", "office", "air_conditioning"],
                "primary_scene": "work",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["work-cold-upper", "work-cold-bottoms", "work-cold-shoes"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
        {
            "name": "rainy_weekend_friends_en",
            "locale": "en-US",
            "weather": {"temperature": 15, "feels_like": 13, "temp_min": 12, "temp_max": 17, "description": "Rain", "humidity": 85, "wind_speed": 3.5},
            "query_context": {
                "query_text": "Shanghai weekend clothes",
                "occasion_text": "meeting friends and walking outside",
                "occasion_tags": ["friends", "walking"],
                "primary_scene": "friends",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["light-rain-hems", "friends-cool-upper", "walking-support"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
        {
            "name": "rainy_weekend_friends_zh",
            "locale": "zh-CN",
            "weather": {"temperature": 15, "feels_like": 13, "temp_min": 12, "temp_max": 17, "description": "Rain", "humidity": 85, "wind_speed": 3.5},
            "query_context": {
                "query_text": "上海周末下雨见朋友怎么穿",
                "occasion_text": "周末见朋友，还要在外面走一走",
                "occasion_tags": ["friends", "walking"],
                "primary_scene": "friends",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["light-rain-hems", "friends-cool-upper", "walking-support"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
        {
            "name": "hot_sunny_date_en",
            "locale": "en-US",
            "weather": {"temperature": 28, "feels_like": 31, "temp_min": 24, "temp_max": 32, "description": "Sunny", "humidity": 62, "wind_speed": 2.2},
            "query_context": {
                "query_text": "Guangzhou outfit advice",
                "occasion_text": "date night with some walking",
                "occasion_tags": ["date", "walking"],
                "primary_scene": "date",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["date-warm-upper", "date-warm-bottoms", "date-warm-shoes"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
        {
            "name": "hot_sunny_date_zh",
            "locale": "zh-CN",
            "weather": {"temperature": 28, "feels_like": 31, "temp_min": 24, "temp_max": 32, "description": "Sunny", "humidity": 62, "wind_speed": 2.2},
            "query_context": {
                "query_text": "广州晴热天气约会穿什么",
                "occasion_text": "晚上约会，还会走一些路",
                "occasion_tags": ["date", "walking"],
                "primary_scene": "date",
                "gender": "neutral",
            },
            "expected_any_hit_ids": ["date-warm-upper", "date-warm-bottoms", "date-warm-shoes"],
            "expected_retrieval_mode": "rules_only",
            "expected_vector_leg_status": "skipped",
        },
    ]


def _evaluate_case_expectations(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    top_hit_ids = list(result.get("top_hit_ids", []))
    final_hit_ids = [str(item.get("knowledge_id", "")) for item in result.get("final_hits", [])]
    retrieval_mode = str(result.get("retrieval_mode", "unknown") or "unknown")
    vector_leg_status = str(result.get("vector_leg_status", "unknown") or "unknown")

    expected_any_hit_ids = [str(item) for item in case.get("expected_any_hit_ids", []) if str(item).strip()]
    if expected_any_hit_ids:
        matched = [item for item in expected_any_hit_ids if item in final_hit_ids]
        checks.append(
            {
                "name": "expected_any_hit_ids",
                "ok": bool(matched),
                "expected": expected_any_hit_ids,
                "actual": final_hit_ids,
                "matched": matched,
            }
        )

    expected_top_hit_ids = [str(item) for item in case.get("expected_top_hit_ids", []) if str(item).strip()]
    if expected_top_hit_ids:
        actual_prefix = top_hit_ids[: len(expected_top_hit_ids)]
        checks.append(
            {
                "name": "expected_top_hit_ids",
                "ok": actual_prefix == expected_top_hit_ids,
                "expected": expected_top_hit_ids,
                "actual": actual_prefix,
            }
        )

    expected_retrieval_mode = str(case.get("expected_retrieval_mode", "") or "").strip()
    if expected_retrieval_mode:
        checks.append(
            {
                "name": "expected_retrieval_mode",
                "ok": retrieval_mode == expected_retrieval_mode,
                "expected": expected_retrieval_mode,
                "actual": retrieval_mode,
            }
        )

    expected_vector_leg_status = str(case.get("expected_vector_leg_status", "") or "").strip()
    if expected_vector_leg_status:
        checks.append(
            {
                "name": "expected_vector_leg_status",
                "ok": vector_leg_status == expected_vector_leg_status,
                "expected": expected_vector_leg_status,
                "actual": vector_leg_status,
            }
        )

    return {
        "checks": checks,
        "check_count": len(checks),
        "passed_check_count": sum(1 for item in checks if item["ok"]),
        "failed_check_count": sum(1 for item in checks if not item["ok"]),
        "passed": all(item["ok"] for item in checks) if checks else None,
    }


def evaluate_retrieval_cases(cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cases = cases or default_retrieval_cases()
    results: list[dict[str, Any]] = []
    for case in cases:
        locale = str(case.get("locale", "en-US") or "en-US")
        weather_payload = dict(case.get("weather", {}))
        weather = WeatherResult(ok=True, city="demo", country="demo", **weather_payload)
        hits, records = knowledge.retrieve_knowledge_hits(
            weather,
            locale=locale,
            query_context=dict(case.get("query_context", {})),
        )
        rule_record = next((item for item in records if item.node_name == "retrieve_knowledge_rules"), None)
        vector_record = next((item for item in records if item.node_name == "retrieve_knowledge_vector"), None)
        rerank_record = next((item for item in records if item.node_name == "rerank_knowledge"), None)
        result = {
            "name": case.get("name", ""),
            "locale": locale,
            "top_hit_ids": [hit.knowledge_id for hit in hits[:3]],
            "top_categories": [hit.category for hit in hits[:3]],
            "retrieval_mode": (rerank_record.metadata if rerank_record else {}).get("retrieval_mode", "unknown"),
            "vector_leg_status": (vector_record.metadata if vector_record else {}).get("vector_leg_status", "unknown"),
            "vector_leg_skipped_reason": (vector_record.metadata if vector_record else {}).get("vector_leg_skipped_reason", ""),
            "rule_hits": (rule_record.metadata if rule_record else {}).get("hits", []),
            "vector_hits": (vector_record.metadata if vector_record else {}).get("hits", []),
            "final_hits": [hit.to_dict() for hit in hits],
        }
        expectation = _evaluate_case_expectations(case, result)
        result.update(expectation)
        results.append(result)

    total_check_count = sum(item["check_count"] for item in results)
    passed_check_count = sum(item["passed_check_count"] for item in results)
    failed_check_count = sum(item["failed_check_count"] for item in results)
    checked_cases = [item for item in results if item["passed"] is not None]

    return {
        "case_count": len(results),
        "checked_case_count": len(checked_cases),
        "passed_case_count": sum(1 for item in checked_cases if item["passed"]),
        "failed_case_count": sum(1 for item in checked_cases if item["passed"] is False),
        "check_count": total_check_count,
        "passed_check_count": passed_check_count,
        "failed_check_count": failed_check_count,
        "cases": results,
    }
