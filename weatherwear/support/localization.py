from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from weatherwear.support.city_aliases import RAW_ALIAS_MAP
from weatherwear.support.common_utils import contains_cjk, normalize_text


COUNTRY_NAMES = {
    "AU": {"zh-CN": "澳大利亚", "en-US": "Australia"},
    "BR": {"zh-CN": "巴西", "en-US": "Brazil"},
    "CA": {"zh-CN": "加拿大", "en-US": "Canada"},
    "CN": {"zh-CN": "中国", "en-US": "China"},
    "DE": {"zh-CN": "德国", "en-US": "Germany"},
    "DEMO": {"zh-CN": "演示数据", "en-US": "Demo"},
    "ES": {"zh-CN": "西班牙", "en-US": "Spain"},
    "FR": {"zh-CN": "法国", "en-US": "France"},
    "GB": {"zh-CN": "英国", "en-US": "United Kingdom"},
    "IN": {"zh-CN": "印度", "en-US": "India"},
    "IT": {"zh-CN": "意大利", "en-US": "Italy"},
    "JP": {"zh-CN": "日本", "en-US": "Japan"},
    "KR": {"zh-CN": "韩国", "en-US": "South Korea"},
    "RU": {"zh-CN": "俄罗斯", "en-US": "Russia"},
    "SG": {"zh-CN": "新加坡", "en-US": "Singapore"},
    "TH": {"zh-CN": "泰国", "en-US": "Thailand"},
    "US": {"zh-CN": "美国", "en-US": "United States"},
}

STATE_NAMES = {
    "bangkok": {"zh-CN": "曼谷", "en-US": "Bangkok"},
    "beijing": {"zh-CN": "北京", "en-US": "Beijing"},
    "england": {"zh-CN": "英格兰", "en-US": "England"},
    "guangdong": {"zh-CN": "广东", "en-US": "Guangdong"},
    "heilongjiang": {"zh-CN": "黑龙江", "en-US": "Heilongjiang"},
    "iledefrance": {"zh-CN": "法兰西岛", "en-US": "Ile-de-France"},
    "macau": {"zh-CN": "澳门", "en-US": "Macau"},
    "newyork": {"zh-CN": "纽约州", "en-US": "New York"},
    "seoul": {"zh-CN": "首尔", "en-US": "Seoul"},
    "shandong": {"zh-CN": "山东", "en-US": "Shandong"},
    "shanghai": {"zh-CN": "上海", "en-US": "Shanghai"},
    "sichuan": {"zh-CN": "四川", "en-US": "Sichuan"},
    "tokyo": {"zh-CN": "东京", "en-US": "Tokyo"},
    "zhejiang": {"zh-CN": "浙江", "en-US": "Zhejiang"},
}

CITY_NAME_OVERRIDES = {
    ("qingzhou", "shandong", "cn"): {"zh-CN": "青州", "en-US": "Qingzhou City"},
    ("ilhaverde", "macau", "cn"): {"zh-CN": "青洲", "en-US": "Ilha Verde"},
    ("macau", "macau", "cn"): {"zh-CN": "澳门", "en-US": "Macau"},
}

WEATHER_DESCRIPTION_MAP = {
    "晴": {"zh-CN": "晴", "en-US": "Clear"},
    "晴天": {"zh-CN": "晴天", "en-US": "Sunny"},
    "晴少云": {"zh-CN": "晴，少云", "en-US": "Clear, few clouds"},
    "少云": {"zh-CN": "少云", "en-US": "Few clouds"},
    "多云": {"zh-CN": "多云", "en-US": "Cloudy"},
    "阴": {"zh-CN": "阴", "en-US": "Overcast"},
    "阴天": {"zh-CN": "阴天", "en-US": "Overcast"},
    "阴多云": {"zh-CN": "阴，多云", "en-US": "Overcast, cloudy"},
    "有风": {"zh-CN": "有风", "en-US": "Windy"},
    "小雨": {"zh-CN": "小雨", "en-US": "Light rain"},
    "中雨": {"zh-CN": "中雨", "en-US": "Moderate rain"},
    "大雨": {"zh-CN": "大雨", "en-US": "Heavy rain"},
    "阵雨": {"zh-CN": "阵雨", "en-US": "Shower rain"},
    "雷暴": {"zh-CN": "雷暴", "en-US": "Thunderstorm"},
    "小雪": {"zh-CN": "小雪", "en-US": "Light snow"},
    "雪": {"zh-CN": "雪", "en-US": "Snow"},
    "雾": {"zh-CN": "雾", "en-US": "Fog"},
    "薄雾": {"zh-CN": "薄雾", "en-US": "Mist"},
    "霾": {"zh-CN": "霾", "en-US": "Haze"},
    "clearsky": {"zh-CN": "晴", "en-US": "Clear"},
    "sunny": {"zh-CN": "晴天", "en-US": "Sunny"},
    "fewclouds": {"zh-CN": "少云", "en-US": "Few clouds"},
    "scatteredclouds": {"zh-CN": "多云", "en-US": "Scattered clouds"},
    "brokenclouds": {"zh-CN": "多云", "en-US": "Broken clouds"},
    "overcastclouds": {"zh-CN": "阴天", "en-US": "Overcast"},
    "cloudy": {"zh-CN": "多云", "en-US": "Cloudy"},
    "lightrain": {"zh-CN": "小雨", "en-US": "Light rain"},
    "moderaterain": {"zh-CN": "中雨", "en-US": "Moderate rain"},
    "heavyrain": {"zh-CN": "大雨", "en-US": "Heavy rain"},
    "showerrain": {"zh-CN": "阵雨", "en-US": "Shower rain"},
    "rain": {"zh-CN": "雨", "en-US": "Rain"},
    "thunderstorm": {"zh-CN": "雷暴", "en-US": "Thunderstorm"},
    "lightsnow": {"zh-CN": "小雪", "en-US": "Light snow"},
    "snow": {"zh-CN": "雪", "en-US": "Snow"},
    "fog": {"zh-CN": "雾", "en-US": "Fog"},
    "mist": {"zh-CN": "薄雾", "en-US": "Mist"},
    "haze": {"zh-CN": "霾", "en-US": "Haze"},
    "windy": {"zh-CN": "有风", "en-US": "Windy"},
}

WEATHER_TOKENS = [
    ("thunderstorm", ["thunderstorm", "storm", "雷暴", "雷雨"]),
    ("light_rain", ["light rain", "小雨"]),
    ("moderate_rain", ["moderate rain", "中雨"]),
    ("heavy_rain", ["heavy rain", "大雨", "暴雨"]),
    ("shower_rain", ["shower rain", "阵雨"]),
    ("rain", ["rain", "drizzle", "雨"]),
    ("light_snow", ["light snow", "小雪"]),
    ("snow", ["snow", "雪"]),
    ("mist", ["mist", "薄雾"]),
    ("fog", ["fog", "雾"]),
    ("haze", ["haze", "霾"]),
    ("windy", ["windy", "wind", "有风"]),
    ("overcast", ["overcast", "阴天", "阴"]),
    ("scattered_clouds", ["scattered clouds"]),
    ("broken_clouds", ["broken clouds"]),
    ("cloudy", ["cloudy", "多云"]),
    ("few_clouds", ["few clouds", "少云"]),
    ("sunny", ["sunny", "晴天"]),
    ("clear", ["clear sky", "clear", "晴"]),
]

WEATHER_TOKEN_LABELS = {
    "thunderstorm": {"zh-CN": "雷暴", "en-US": "Thunderstorm"},
    "light_rain": {"zh-CN": "小雨", "en-US": "Light rain"},
    "moderate_rain": {"zh-CN": "中雨", "en-US": "Moderate rain"},
    "heavy_rain": {"zh-CN": "大雨", "en-US": "Heavy rain"},
    "shower_rain": {"zh-CN": "阵雨", "en-US": "Shower rain"},
    "rain": {"zh-CN": "雨", "en-US": "Rain"},
    "light_snow": {"zh-CN": "小雪", "en-US": "Light snow"},
    "snow": {"zh-CN": "雪", "en-US": "Snow"},
    "mist": {"zh-CN": "薄雾", "en-US": "Mist"},
    "fog": {"zh-CN": "雾", "en-US": "Fog"},
    "haze": {"zh-CN": "霾", "en-US": "Haze"},
    "windy": {"zh-CN": "有风", "en-US": "Windy"},
    "overcast": {"zh-CN": "阴天", "en-US": "Overcast"},
    "scattered_clouds": {"zh-CN": "多云", "en-US": "Scattered clouds"},
    "broken_clouds": {"zh-CN": "多云", "en-US": "Broken clouds"},
    "cloudy": {"zh-CN": "多云", "en-US": "Cloudy"},
    "few_clouds": {"zh-CN": "少云", "en-US": "Few clouds"},
    "sunny": {"zh-CN": "晴天", "en-US": "Sunny"},
    "clear": {"zh-CN": "晴", "en-US": "Clear"},
}

ADMIN_SUFFIXES = (
    "specialadministrativeregion",
    "municipality",
    "province",
    "district",
    "county",
    "region",
    "city",
    "sar",
    "特别行政区",
    "自治区",
    "地区",
    "城区",
    "省",
    "市",
    "区",
    "县",
)


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _locale_key(locale: str) -> str:
    return "en-US" if _is_english(locale) else "zh-CN"


def _normalized_variants(text: str = "") -> set[str]:
    base = normalize_text(text)
    if not base:
        return set()
    variants = {base}
    queue = [base]
    while queue:
        current = queue.pop()
        for suffix in ADMIN_SUFFIXES:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                trimmed = current[: -len(suffix)]
                if trimmed and trimmed not in variants:
                    variants.add(trimmed)
                    queue.append(trimmed)
    if "macausar" in variants:
        variants.add("macau")
    if "macaosar" in variants:
        variants.add("macao")
    return variants


def _primary_variant(text: str = "") -> str:
    variants = _normalized_variants(text)
    if not variants:
        return ""
    return min(variants, key=lambda value: (len(value), value))


def _country_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for code, labels in COUNTRY_NAMES.items():
        lookup[normalize_text(code)] = code
        for label in labels.values():
            lookup[normalize_text(label)] = code
    return lookup


@lru_cache(maxsize=1)
def _state_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for key, labels in STATE_NAMES.items():
        for candidate in {key, labels["zh-CN"], labels["en-US"]}:
            for variant in _normalized_variants(candidate):
                lookup[variant] = labels
    return lookup


@lru_cache(maxsize=1)
def _city_records() -> list[dict[str, Any]]:
    records: dict[tuple[str, str, str], dict[str, Any]] = {}
    for alias_key, payload in RAW_ALIAS_MAP.items():
        city = str(payload.get("city", "")).strip()
        state = str(payload.get("state", "")).strip()
        country = str(payload.get("country", "")).strip()
        country_code = str(payload.get("country_code", "")).strip()
        if not city:
            continue

        city_key = _primary_variant(city)
        state_key = _primary_variant(state)
        country_key = normalize_text(country_code or country)
        record_key = (city_key, state_key, country_key)
        record = records.setdefault(
            record_key,
            {
                "en_name": city,
                "zh_name": "",
                "state_key": state_key,
                "country_key": country_key,
                "match_keys": set(),
            },
        )
        record["match_keys"].update(_normalized_variants(city))
        record["match_keys"].update(_normalized_variants(alias_key))
        if contains_cjk(alias_key) and not record["zh_name"]:
            record["zh_name"] = str(alias_key)

    for (city_key, state_key, country_key), labels in CITY_NAME_OVERRIDES.items():
        record = records.setdefault(
            (city_key, state_key, country_key),
            {
                "en_name": labels["en-US"],
                "zh_name": labels["zh-CN"],
                "state_key": state_key,
                "country_key": country_key,
                "match_keys": set(),
            },
        )
        record["en_name"] = record["en_name"] or labels["en-US"]
        record["zh_name"] = record["zh_name"] or labels["zh-CN"]
        record["match_keys"].update(_normalized_variants(labels["en-US"]))
        record["match_keys"].update(_normalized_variants(labels["zh-CN"]))
    return list(records.values())


def _matches_region(record_value: str, query_values: set[str]) -> bool:
    if not record_value or not query_values:
        return True
    return any(
        record_value == candidate or record_value in candidate or candidate in record_value
        for candidate in query_values
        if candidate
    )


def _match_city_record(city: str = "", state: str = "", country: str = "", country_code: str = "") -> dict[str, Any] | None:
    city_values = _normalized_variants(city)
    if not city_values:
        return None
    state_values = _normalized_variants(state)
    country_values = {normalize_text(country_code), normalize_text(country)} - {""}

    best_record: dict[str, Any] | None = None
    best_score = -1
    for record in _city_records():
        if not _matches_region(record["state_key"], state_values):
            continue
        if not _matches_region(record["country_key"], country_values):
            continue

        score = -1
        for city_value in city_values:
            for match_key in record["match_keys"]:
                if city_value == match_key:
                    score = max(score, 1000 + len(match_key))
                elif match_key and (match_key in city_value or city_value in match_key):
                    score = max(score, len(match_key))
        if score > best_score:
            best_record = record
            best_score = score
    return best_record if best_score > 0 else None


def _fallback_english_city(city: str = "") -> str:
    if not city:
        return ""
    ascii_only = re.sub(r"[^A-Za-z0-9 .,'-]+", " ", city)
    ascii_only = re.sub(r"\s+", " ", ascii_only).strip(" ,")
    return ascii_only or city


def localize_country_name(country: str = "", country_code: str = "", locale: str = "zh-CN") -> str:
    code = str(country_code or "").upper()
    if not code and country:
        code = _country_lookup().get(normalize_text(country), "")
    if code and code in COUNTRY_NAMES:
        return COUNTRY_NAMES[code][_locale_key(locale)]
    return country


def localize_state_name(state: str = "", locale: str = "zh-CN") -> str:
    if not state:
        return state
    for variant in _normalized_variants(state):
        labels = _state_lookup().get(variant)
        if labels:
            return labels[_locale_key(locale)]
    return state


def localize_city_name(
    city: str = "",
    state: str = "",
    country: str = "",
    country_code: str = "",
    locale: str = "zh-CN",
) -> str:
    if not city:
        return city
    record = _match_city_record(city, state, country, country_code)
    if _is_english(locale):
        if record and record.get("en_name"):
            return str(record["en_name"])
        return _fallback_english_city(city)
    if record and record.get("zh_name"):
        return str(record["zh_name"])
    return city


def localize_location_label(
    city: str = "",
    state: str = "",
    country: str = "",
    country_code: str = "",
    locale: str = "zh-CN",
) -> str:
    localized_city = localize_city_name(city, state, country, country_code, locale)
    localized_state = localize_state_name(state, locale)
    localized_country = localize_country_name(country, country_code, locale)

    separator = ", " if _is_english(locale) else "，"
    parts: list[str] = []
    for part in (localized_city, localized_state, localized_country):
        text = str(part or "").strip()
        if not text:
            continue
        if parts and normalize_text(parts[-1]) == normalize_text(text):
            continue
        parts.append(text)
    return separator.join(parts)


def localize_weather_description(description: str = "", locale: str = "zh-CN") -> str:
    text = str(description or "").strip()
    if not text:
        return ""

    locale_key = _locale_key(locale)
    normalized = normalize_text(text)
    direct = WEATHER_DESCRIPTION_MAP.get(normalized)
    if direct:
        return direct[locale_key]

    tokens: list[str] = []
    for token_key, markers in WEATHER_TOKENS:
        if any(normalize_text(marker) and normalize_text(marker) in normalized for marker in markers):
            tokens.append(token_key)

    if not tokens:
        return text

    deduped: list[str] = []
    for token in tokens:
        if token not in deduped:
            deduped.append(token)

    parts = [WEATHER_TOKEN_LABELS[token][locale_key] for token in deduped if token in WEATHER_TOKEN_LABELS]
    if not parts:
        return text
    separator = ", " if _is_english(locale) else "，"
    return separator.join(parts)
