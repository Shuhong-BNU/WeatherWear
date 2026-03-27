from __future__ import annotations

import hashlib
import re
import sys
from difflib import SequenceMatcher


QUERY_NOISE_PATTERNS = [
    r"请帮我",
    r"帮我",
    r"请查询",
    r"查询一下",
    r"查询",
    r"看一下",
    r"看看",
    r"告诉我",
    r"请问",
    r"天气怎么样",
    r"天气如何",
    r"天气",
    r"穿衣建议",
    r"穿搭建议",
    r"衣着建议",
    r"并给出",
    r"并提供",
    r"给出",
    r"提供",
    r"适合穿什么",
    r"怎么穿",
    r"今天",
    r"现在",
]

COMPLEX_QUERY_MARKERS = [
    "明天",
    "后天",
    "未来",
    "预报",
    "几点",
    "什么时候",
    "适合",
    "推荐",
    "怎么穿",
    "如何穿",
    "要不要",
    "出门",
    "安排",
    "and",
    "with",
]


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text.casefold()
    cleaned = re.sub(r"[\s,，。！？!?:：;；'\"“”‘’\-_/\\()（）\[\]{}]+", "", cleaned)
    return cleaned


def strip_query_noise(text: str | None) -> str:
    if not text:
        return ""
    cleaned = (text or "").strip()
    for pattern in QUERY_NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,，。！？!?")
    return cleaned or (text or "").strip()


def contains_cjk(text: str | None) -> bool:
    if not text:
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def similarity_score(left: str | None, right: str | None) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def compose_location_label(city: str = "", state: str = "", country: str = "") -> str:
    parts = [part for part in [city, state, country] if part]
    return ", ".join(parts)


def compact_text(text: str | None, max_len: int = 120) -> str:
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", str(text)).strip()
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3] + "..."


def extract_probable_location(text: str | None) -> str:
    cleaned = strip_query_noise(text)
    cleaned = re.sub(r"(的)?(实时)?(当前)?(当地)?$", "", cleaned).strip(" ,，。！？!?")
    return cleaned or (text or "").strip()


def is_complex_weather_query(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False

    probable_location = extract_probable_location(raw)
    raw_norm = normalize_text(raw)
    location_norm = normalize_text(probable_location)
    token_count = len(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", raw))

    if len(raw) >= 28 or token_count >= 7:
        return True
    if any(marker in raw.casefold() for marker in [marker.casefold() for marker in COMPLEX_QUERY_MARKERS]):
        return True
    if any(marker in raw for marker in ["?", "？", "。", ";", "；"]):
        return True
    if raw.count("，") + raw.count(",") >= 2:
        return True
    if raw_norm and location_norm and len(location_norm) / max(len(raw_norm), 1) < 0.55:
        return True
    return False


def has_explicit_region_hint(text: str | None) -> bool:
    if not text:
        return False
    lowered = str(text).casefold()
    markers = [
        ",",
        "，",
        "省",
        "州",
        "国",
        "英国",
        "法国",
        "美国",
        "中国",
        "日本",
        "韩国",
        "泰国",
        "england",
        "france",
        "china",
        "japan",
        "korea",
        "thailand",
        "usa",
        "united states",
        "united kingdom",
        "county",
        "district",
    ]
    return any(marker in lowered for marker in markers)


def stable_id(*parts: str) -> str:
    raw = "||".join(part or "" for part in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def unique_by(items, key_func):
    seen = set()
    results = []
    for item in items:
        key = key_func(item)
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def safe_console_print(text: str):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = str(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe_text)
