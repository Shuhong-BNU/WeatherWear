from __future__ import annotations

import json
import time
from typing import Any

from weatherwear.domain.types import ExecutionRecord
from weatherwear.support.common_utils import compact_text, normalize_text
from weatherwear.support.llm_support import get_llm_config, run_agent


RULE_TAGS = {
    "work": ["上班", "通勤", "办公室", "office", "work", "meeting", "商务", "formal"],
    "date": ["约会", "date", "romantic"],
    "friends": ["见朋友", "朋友", "聚会", "hangout", "friends", "weekend"],
    "home": ["在家", "居家", "home", "indoors", "宅家"],
    "exercise": ["运动", "跑步", "健身", "exercise", "run", "gym", "training", "骑行"],
    "travel": ["旅行", "旅游", "trip", "travel"],
    "walking": ["走很多路", "步行", "walking", "walk", "city stroll"],
    "outdoor": ["户外", "outside", "outdoor"],
    "indoor": ["室内", "inside", "indoor"],
    "air_conditioning": ["空调", "ac", "air conditioning"],
    "formal": ["正式", "西装", "formal", "smart casual"],
    "casual": ["休闲", "casual", "relaxed"],
}
PRIMARY_SCENES = ["work", "date", "friends", "home", "exercise", "travel"]


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _msg(locale: str, zh: str, en: str) -> str:
    return en if _is_english(locale) else zh


def _rule_extract_tags(occasion_text: str) -> list[str]:
    normalized = normalize_text(occasion_text)
    tags: list[str] = []
    for tag, keywords in RULE_TAGS.items():
        if any(normalize_text(keyword) in normalized for keyword in keywords):
            tags.append(tag)
    return tags


def _split_occasion_context(tags: list[str]) -> tuple[str, list[str]]:
    primary_scene = next((scene for scene in PRIMARY_SCENES if scene in tags), "")
    context_tags = [tag for tag in tags if tag != primary_scene]
    return primary_scene, context_tags


def _llm_extract_tags(occasion_text: str, locale: str, cancel_token: object | None = None) -> tuple[list[str], ExecutionRecord]:
    system_prompt = (
        "Return strict JSON only. "
        'Schema: {"tags":["work","date","friends","home","exercise","travel","walking","outdoor","indoor","air_conditioning","formal","casual"]}. '
        "Choose only tags supported by the input."
    )
    prompt = f"User occasion text: {occasion_text}"
    output, record = run_agent(
        role=_msg(locale, "场合提取", "Occasion extraction"),
        name="OccasionParser",
        system_prompt=system_prompt,
        prompt=prompt,
        json_mode=True,
        cancel_token=cancel_token,
    )
    record.node_name = "extract_occasion"
    record.decision_reason = "occasion_text_to_tags"
    if not record.success or not output:
        return [], record
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        record.success = False
        record.error = "occasion_tags_invalid_json"
        return [], record
    raw_tags = payload.get("tags", []) if isinstance(payload, dict) else []
    tags = [str(tag) for tag in raw_tags if str(tag) in RULE_TAGS]
    return tags, record


def extract_occasion_tags(
    occasion_text: str,
    *,
    locale: str = "zh-CN",
    cancel_token: object | None = None,
) -> tuple[list[str], ExecutionRecord]:
    tags = _rule_extract_tags(occasion_text)
    record = ExecutionRecord(
        role=_msg(locale, "场合提取", "Occasion extraction"),
        name="OccasionRules",
        node_name="extract_occasion",
        provider="rule_extractor",
        success=True,
        used_llm=False,
        fallback_used=False,
        input_summary=compact_text(occasion_text, max_len=120),
        output_summary=compact_text(", ".join(tags) or "-", max_len=120),
        metadata={"occasion_text": occasion_text, "tags": tags},
        decision_reason="rule_keywords",
    )
    if tags or len(occasion_text.strip()) < 6:
        return tags, record
    llm_config = get_llm_config()
    if not llm_config.get("enabled"):
        return tags, record
    llm_tags, llm_record = _llm_extract_tags(occasion_text, locale, cancel_token=cancel_token)
    if llm_tags:
        return llm_tags, llm_record
    return tags, llm_record


def extract_occasion_context(
    occasion_text: str,
    *,
    locale: str = "zh-CN",
    cancel_token: object | None = None,
) -> tuple[dict[str, Any], ExecutionRecord]:
    started_at = time.time()
    tags, record = extract_occasion_tags(occasion_text, locale=locale, cancel_token=cancel_token)
    primary_scene, context_tags = _split_occasion_context(tags)
    record.elapsed_ms = record.elapsed_ms or int((time.time() - started_at) * 1000)
    record.step_kind = "occasion_parse"
    record.metadata = {
        **(record.metadata or {}),
        "occasion_text": occasion_text,
        "tags": tags,
        "primary_scene": primary_scene,
        "context_tags": context_tags,
    }
    record.output_summary = compact_text(", ".join([primary_scene, *context_tags]) or "-", max_len=120)
    return {
        "tags": tags,
        "primary_scene": primary_scene,
        "context_tags": context_tags,
    }, record
