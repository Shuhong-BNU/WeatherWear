from __future__ import annotations

import copy
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv

from app_types import LocationCandidate, WeatherResult
from city_aliases import COMMON_CITY_ALIASES, COUNTRY_NAME_BY_CODE
from common_utils import compose_location_label, normalize_text, similarity_score, stable_id

load_dotenv()


class Weather:
    """天气服务，优先使用地理编码 + 经纬度查询。"""

    GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"
    WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
    _SESSION: requests.Session | None = None
    _CACHE: dict[str, tuple[float, Any]] = {}
    _CACHE_LOCK = threading.Lock()

    def __init__(self, api_key: str | None = None, unit: str = "metric", timeout: int = 8):
        self.api_key = (api_key if api_key is not None else os.environ.get("OPENWEATHER_API_KEY", "")).strip()
        self.unit = unit
        self.timeout = timeout
        self.demo_mode = not bool(self.api_key)
        if Weather._SESSION is None:
            Weather._SESSION = requests.Session()
            Weather._SESSION.headers.update({"User-Agent": "FashionDailyDress/2.2"})
        self.session = Weather._SESSION

    @classmethod
    def _cache_get(cls, key: str) -> Any | None:
        with cls._CACHE_LOCK:
            record = cls._CACHE.get(key)
            if not record:
                return None
            expires_at, payload = record
            if expires_at < time.time():
                cls._CACHE.pop(key, None)
                return None
            return copy.deepcopy(payload)

    @classmethod
    def _cache_set(cls, key: str, payload: Any, ttl_seconds: int):
        with cls._CACHE_LOCK:
            cls._CACHE[key] = (time.time() + ttl_seconds, copy.deepcopy(payload))

    def _request_json(
        self,
        url: str,
        params: dict[str, Any],
        *,
        cache_key: str,
        ttl_seconds: int,
    ) -> tuple[Any | None, str]:
        if self.demo_mode:
            return None, "missing_openweather_api_key"

        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached, ""

        last_error = "unknown_error"
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                data = response.json()
            except Exception as exc:
                last_error = f"请求异常: {exc}"
                if attempt < 2:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                return None, last_error

            if response.status_code == 200:
                self._cache_set(cache_key, data, ttl_seconds)
                return data, ""

            message = data.get("message", "请求失败") if isinstance(data, dict) else "请求失败"
            last_error = f"HTTP {response.status_code}: {message}"
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(0.35 * (attempt + 1))
                continue
            break

        return None, last_error

    def _country_name(self, country_code: str, fallback_country: str = "") -> str:
        if country_code and country_code in COUNTRY_NAME_BY_CODE:
            return COUNTRY_NAME_BY_CODE[country_code]
        return fallback_country or country_code

    def _candidate_from_geo(
        self,
        item: dict[str, Any],
        confidence: float,
        source: str,
        query_text: str,
        rank: int,
    ) -> LocationCandidate:
        city = str(item.get("name", ""))
        state = str(item.get("state", ""))
        country_code = str(item.get("country", ""))
        country = self._country_name(country_code)
        display_name = compose_location_label(city, state, country)
        return LocationCandidate(
            candidate_id=stable_id(city, state, country_code, str(item.get("lat")), str(item.get("lon"))),
            city=city,
            state=state,
            country=country,
            country_code=country_code,
            lat=item.get("lat"),
            lon=item.get("lon"),
            confidence=round(max(0.0, min(1.0, confidence)), 3),
            source=source,
            query_text=query_text,
            display_name=display_name,
            metadata={"rank": rank, "raw_query": query_text},
        )

    def _alias_candidate(self, query: str) -> LocationCandidate | None:
        alias_seed = COMMON_CITY_ALIASES.get(normalize_text(query))
        if not alias_seed:
            return None
        city = str(alias_seed.get("city", query))
        state = str(alias_seed.get("state", ""))
        country_code = str(alias_seed.get("country_code", ""))
        country = str(alias_seed.get("country", self._country_name(country_code)))
        lat = alias_seed.get("lat")
        lon = alias_seed.get("lon")
        return LocationCandidate(
            candidate_id=stable_id(city, state, country_code, str(lat), str(lon)),
            city=city,
            state=state,
            country=country,
            country_code=country_code,
            lat=lat,
            lon=lon,
            confidence=0.97,
            source="alias_seed",
            query_text=query,
            display_name=compose_location_label(city, state, country),
            metadata={"rank": 0, "raw_query": query},
        )

    def geocode_city(self, query: str, limit: int = 5) -> list[LocationCandidate]:
        if not query:
            return []

        alias_candidate = self._alias_candidate(query)
        if self.demo_mode:
            return [alias_candidate] if alias_candidate else []

        data, error = self._request_json(
            self.GEO_URL,
            {"q": query, "limit": limit, "appid": self.api_key},
            cache_key=f"geo::{normalize_text(query)}::{limit}",
            ttl_seconds=1800,
        )
        if error or not isinstance(data, list):
            return [alias_candidate] if alias_candidate else []

        candidates: list[LocationCandidate] = []
        if alias_candidate:
            candidates.append(alias_candidate)
        for index, item in enumerate(data[:limit]):
            base_confidence = max(0.38, 0.82 - index * 0.07)
            candidates.append(
                self._candidate_from_geo(
                    item,
                    confidence=base_confidence,
                    source="geocoding",
                    query_text=query,
                    rank=index,
                )
            )
        return candidates

    def validate_candidate(self, candidate: LocationCandidate) -> list[LocationCandidate]:
        queries: list[str] = []
        primary_query = ",".join(
            part for part in [candidate.city, candidate.state, candidate.country_code or candidate.country] if part
        )
        if primary_query:
            queries.append(primary_query)
        if candidate.query_text and candidate.query_text not in queries:
            queries.append(candidate.query_text)

        source_bonus_map = {
            "alias_seed": 0.14,
            "llm_resolution": 0.07,
            "raw_input": 0.02,
            "direct_geocoding": 0.04,
            "geocoding": 0.05,
        }
        validated: list[LocationCandidate] = []
        for query in queries:
            resolved_candidates = self.geocode_city(query, limit=6)
            for resolved in resolved_candidates:
                city_score = similarity_score(candidate.city or candidate.query_text, resolved.city)
                state_score = similarity_score(candidate.state, resolved.state)
                country_score = similarity_score(
                    candidate.country_code or candidate.country,
                    resolved.country_code or resolved.country,
                )
                query_score = similarity_score(candidate.query_text, resolved.display_name or resolved.city)
                source_bonus = source_bonus_map.get(candidate.source, 0.0)
                final_confidence = (
                    0.35 * resolved.confidence
                    + 0.28 * city_score
                    + 0.12 * state_score
                    + 0.10 * country_score
                    + 0.08 * query_score
                    + source_bonus
                    + min(candidate.confidence, 1.0) * 0.07
                )
                if city_score < 0.45 and normalize_text(candidate.query_text) != normalize_text(query):
                    continue
                resolved.confidence = round(max(0.0, min(0.99, final_confidence)), 3)
                if candidate.country and country_score >= 0.8:
                    resolved.country = candidate.country
                if candidate.country_code and not resolved.country_code:
                    resolved.country_code = candidate.country_code
                if candidate.state and not resolved.state:
                    resolved.state = candidate.state
                resolved.display_name = compose_location_label(
                    resolved.city,
                    resolved.state,
                    resolved.country or self._country_name(resolved.country_code),
                )
                resolved.metadata["matched_query"] = query
                resolved.metadata["city_score"] = city_score
                resolved.metadata["state_score"] = state_score
                resolved.metadata["country_score"] = country_score
                resolved.metadata["query_score"] = query_score
                validated.append(resolved)

        if not validated and candidate.lat is not None and candidate.lon is not None:
            validated.append(candidate)

        return validated

    def _timezone_from_offset(self, offset_seconds: int):
        return timezone(timedelta(seconds=offset_seconds))

    def _format_epoch(self, epoch_value: int | float | None, offset_seconds: int = 0) -> tuple[str, str]:
        if epoch_value is None:
            return "", ""
        dt_utc = datetime.fromtimestamp(float(epoch_value), tz=timezone.utc)
        dt_local = dt_utc.astimezone(self._timezone_from_offset(offset_seconds))
        return dt_utc.isoformat(timespec="seconds"), dt_local.strftime("%Y-%m-%d %H:%M")

    def _current_city_time(self, offset_seconds: int) -> str:
        return datetime.now(timezone.utc).astimezone(
            self._timezone_from_offset(offset_seconds)
        ).strftime("%Y-%m-%d %H:%M")

    def _build_range_text(
        self,
        temp_min: float | None,
        temp_max: float | None,
        temperature_unit: str,
    ) -> str:
        if temp_min is None or temp_max is None:
            return ""
        return f"{temp_min}{temperature_unit} ~ {temp_max}{temperature_unit}"

    def _fetch_daily_range(
        self,
        lat: float,
        lon: float,
        *,
        lang: str,
        reference_epoch: int | float | None,
        fallback_min: float | None,
        fallback_max: float | None,
    ) -> tuple[float | None, float | None]:
        if self.demo_mode:
            return fallback_min, fallback_max

        data, error = self._request_json(
            self.FORECAST_URL,
            {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": self.unit,
                "lang": lang,
            },
            cache_key=f"forecast::{round(lat, 4)}::{round(lon, 4)}::{lang}::{self.unit}",
            ttl_seconds=900,
        )
        if error or not isinstance(data, dict):
            return fallback_min, fallback_max

        city_info = data.get("city", {}) if isinstance(data.get("city"), dict) else {}
        timezone_offset = int(city_info.get("timezone", 0) or 0)
        reference_value = reference_epoch if reference_epoch is not None else time.time()
        reference_local = datetime.fromtimestamp(
            float(reference_value),
            tz=timezone.utc,
        ).astimezone(self._timezone_from_offset(timezone_offset))
        target_date = reference_local.date()

        highs: list[float] = []
        lows: list[float] = []
        items = data.get("list", [])
        if not isinstance(items, list):
            return fallback_min, fallback_max

        for item in items:
            if not isinstance(item, dict):
                continue
            item_epoch = item.get("dt")
            main_data = item.get("main", {}) if isinstance(item.get("main"), dict) else {}
            if item_epoch is None:
                continue
            item_local = datetime.fromtimestamp(float(item_epoch), tz=timezone.utc).astimezone(
                self._timezone_from_offset(timezone_offset)
            )
            if item_local.date() != target_date:
                continue
            high = main_data.get("temp_max", main_data.get("temp"))
            low = main_data.get("temp_min", main_data.get("temp"))
            if high is not None:
                highs.append(float(high))
            if low is not None:
                lows.append(float(low))

        if not highs or not lows:
            for item in items[:8]:
                if not isinstance(item, dict):
                    continue
                main_data = item.get("main", {}) if isinstance(item.get("main"), dict) else {}
                high = main_data.get("temp_max", main_data.get("temp"))
                low = main_data.get("temp_min", main_data.get("temp"))
                if high is not None:
                    highs.append(float(high))
                if low is not None:
                    lows.append(float(low))

        if not highs or not lows:
            return fallback_min, fallback_max

        return round(min(lows), 1), round(max(highs), 1)

    def _build_demo_weather(self, location: LocationCandidate | None = None) -> WeatherResult:
        if location is None:
            return WeatherResult(
                ok=False,
                source="demo_weather",
                data_mode="error",
                error="缺少可用于 demo 的城市位置。",
            )

        seed = normalize_text(location.query_text or location.city or "demo")
        checksum = sum(ord(char) for char in seed) or 42
        temperature = float(8 + checksum % 26)
        feels_like = float(temperature + (checksum % 5 - 2))
        temp_min = round(temperature - (2 + checksum % 3), 1)
        temp_max = round(temperature + (3 + checksum % 4), 1)
        descriptions = ["晴天", "多云", "小雨", "阴天", "有风"]
        description = descriptions[checksum % len(descriptions)]
        humidity = 40 + checksum % 40
        wind_speed = round(1 + (checksum % 40) / 10, 1)
        now_epoch = int(time.time())
        observed_at, observed_at_local = self._format_epoch(now_epoch, 0)
        return WeatherResult(
            ok=True,
            city=location.city,
            state=location.state,
            country=location.country or self._country_name(location.country_code),
            country_code=location.country_code,
            lat=location.lat,
            lon=location.lon,
            temperature=temperature,
            feels_like=feels_like,
            temp_min=temp_min,
            temp_max=temp_max,
            description=description,
            humidity=humidity,
            wind_speed=wind_speed,
            observed_at=observed_at,
            observed_at_local=observed_at_local,
            city_local_time=observed_at_local,
            timezone_offset=0,
            daily_range_text=self._build_range_text(temp_min, temp_max, "°C"),
            source="demo_weather",
            data_mode="demo",
            demo_mode=True,
            fallback_used=True,
        )

    def _error_result(
        self,
        error: str,
        *,
        source: str,
        location: LocationCandidate | None = None,
        fallback_used: bool = False,
        request_elapsed_ms: int = 0,
    ) -> WeatherResult:
        return WeatherResult(
            ok=False,
            city=location.city if location else "",
            state=location.state if location else "",
            country=location.country if location else "",
            country_code=location.country_code if location else "",
            lat=location.lat if location else None,
            lon=location.lon if location else None,
            source=source,
            data_mode="error",
            fallback_used=fallback_used,
            request_elapsed_ms=request_elapsed_ms,
            error=error,
        )

    def _parse_weather_data(
        self,
        data: dict[str, Any],
        *,
        location: LocationCandidate | None,
        source: str,
        data_mode: str,
        fallback_used: bool,
        lang: str,
    ) -> WeatherResult:
        weather_summary = data.get("weather", [{}])[0] if isinstance(data.get("weather"), list) else {}
        main_data = data.get("main", {}) if isinstance(data.get("main"), dict) else {}
        wind_data = data.get("wind", {}) if isinstance(data.get("wind"), dict) else {}
        sys_data = data.get("sys", {}) if isinstance(data.get("sys"), dict) else {}
        country_code = location.country_code if location and location.country_code else str(sys_data.get("country", ""))
        timezone_offset = int(data.get("timezone", 0) or 0)
        observed_epoch = data.get("dt")
        observed_at, observed_at_local = self._format_epoch(observed_epoch, timezone_offset)

        temp_min = main_data.get("temp_min")
        temp_max = main_data.get("temp_max")
        lat = location.lat if location and location.lat is not None else data.get("coord", {}).get("lat")
        lon = location.lon if location and location.lon is not None else data.get("coord", {}).get("lon")
        if lat is not None and lon is not None:
            temp_min, temp_max = self._fetch_daily_range(
                float(lat),
                float(lon),
                lang=lang,
                reference_epoch=observed_epoch,
                fallback_min=float(temp_min) if temp_min is not None else None,
                fallback_max=float(temp_max) if temp_max is not None else None,
            )

        result = WeatherResult(
            ok=True,
            city=location.city if location and location.city else str(data.get("name", "")),
            state=location.state if location else "",
            country=(location.country if location and location.country else self._country_name(country_code)),
            country_code=country_code,
            lat=lat,
            lon=lon,
            temperature=main_data.get("temp"),
            feels_like=main_data.get("feels_like"),
            temp_min=temp_min,
            temp_max=temp_max,
            description=str(weather_summary.get("description", "")),
            humidity=main_data.get("humidity"),
            wind_speed=wind_data.get("speed"),
            observed_at=observed_at,
            observed_at_local=observed_at_local,
            city_local_time=self._current_city_time(timezone_offset),
            timezone_offset=timezone_offset,
            daily_range_text=self._build_range_text(temp_min, temp_max, "°C"),
            source=source,
            data_mode=data_mode,
            demo_mode=(data_mode == "demo"),
            fallback_used=fallback_used,
            raw=data,
        )
        return result

    def _get_weather_by_city_query(self, query: str, lang: str = "zh_cn") -> WeatherResult:
        started_at = time.time()
        location = self._alias_candidate(query) or LocationCandidate(
            candidate_id=stable_id(query, "", "", "", ""),
            city=query,
            query_text=query,
            display_name=query,
        )
        if self.demo_mode:
            if location and location.lat is not None and location.lon is not None:
                result = self._build_demo_weather(location)
                result.request_elapsed_ms = int((time.time() - started_at) * 1000)
                return result
            return self._error_result(
                "未配置 OPENWEATHER_API_KEY，且本地没有该城市的演示数据。",
                source="openweather_q_fallback",
                location=location,
                fallback_used=True,
                request_elapsed_ms=int((time.time() - started_at) * 1000),
            )

        data, error = self._request_json(
            self.WEATHER_URL,
            {
                "q": query,
                "appid": self.api_key,
                "units": self.unit,
                "lang": lang,
            },
            cache_key=f"weather_q::{normalize_text(query)}::{lang}::{self.unit}",
            ttl_seconds=180,
        )
        if error or not isinstance(data, dict):
            return self._error_result(
                error or "q 查询失败。",
                source="openweather_q_fallback",
                location=location,
                fallback_used=True,
                request_elapsed_ms=int((time.time() - started_at) * 1000),
            )

        location.city = str(data.get("name", location.city))
        result = self._parse_weather_data(
            data,
            location=location,
            source="openweather_q_fallback",
            data_mode="real_q_fallback",
            fallback_used=True,
            lang=lang,
        )
        result.request_elapsed_ms = int((time.time() - started_at) * 1000)
        return result

    def get_weather_by_coords(
        self,
        lat: float,
        lon: float,
        lang: str = "zh_cn",
        location: LocationCandidate | None = None,
        *,
        allow_q_fallback: bool = True,
    ) -> WeatherResult:
        started_at = time.time()
        if self.demo_mode:
            result = self._build_demo_weather(location)
            result.request_elapsed_ms = int((time.time() - started_at) * 1000)
            return result

        data, error = self._request_json(
            self.WEATHER_URL,
            {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": self.unit,
                "lang": lang,
            },
            cache_key=f"weather_latlon::{round(lat, 4)}::{round(lon, 4)}::{lang}::{self.unit}",
            ttl_seconds=180,
        )
        if error or not isinstance(data, dict):
            query = location.query_text if location and location.query_text else location.city if location else ""
            if allow_q_fallback and query:
                q_result = self._get_weather_by_city_query(query, lang=lang)
                if q_result.ok:
                    q_result.error = error
                    q_result.request_elapsed_ms = int((time.time() - started_at) * 1000)
                    return q_result
            return self._error_result(
                error or "经纬度天气查询失败。",
                source="openweather_latlon",
                location=location,
                fallback_used=allow_q_fallback and bool(query),
                request_elapsed_ms=int((time.time() - started_at) * 1000),
            )

        result = self._parse_weather_data(
            data,
            location=location,
            source="openweather_latlon",
            data_mode="real_latlon",
            fallback_used=False,
            lang=lang,
        )
        result.request_elapsed_ms = int((time.time() - started_at) * 1000)
        return result

    def get_weather_for_candidate(
        self,
        candidate: LocationCandidate,
        lang: str = "zh_cn",
        *,
        allow_q_fallback: bool = True,
    ) -> WeatherResult:
        working_candidate = candidate
        if working_candidate.lat is None or working_candidate.lon is None:
            fallback_candidates = self.validate_candidate(working_candidate)
            if fallback_candidates:
                working_candidate = fallback_candidates[0]

        if working_candidate.lat is None or working_candidate.lon is None:
            if allow_q_fallback:
                return self._get_weather_by_city_query(working_candidate.query_text or working_candidate.city, lang=lang)
            return self._error_result(
                "没有足够的位置坐标，且当前策略不允许 q 查询兜底。",
                source="openweather_latlon",
                location=working_candidate,
            )

        return self.get_weather_by_coords(
            float(working_candidate.lat),
            float(working_candidate.lon),
            lang=lang,
            location=working_candidate,
            allow_q_fallback=allow_q_fallback,
        )

    def get_weather_by_query(self, query: str, lang: str = "zh_cn") -> WeatherResult:
        candidates = self.geocode_city(query, limit=1)
        if candidates:
            return self.get_weather_for_candidate(candidates[0], lang=lang, allow_q_fallback=True)
        if self.demo_mode:
            alias_candidate = self._alias_candidate(query)
            if alias_candidate:
                return self._build_demo_weather(alias_candidate)
        return self._error_result("无法解析城市位置。", source="query_resolution")

    def format_weather(self, weather_result: WeatherResult) -> str:
        if not weather_result.ok:
            return (
                f"天气查询失败: {weather_result.error or '未知错误'}\n"
                f"数据模式: {weather_result.data_mode}\n"
                f"数据来源: {weather_result.source}"
            )

        location_label = compose_location_label(
            weather_result.city,
            weather_result.state,
            weather_result.country,
        )
        range_line = weather_result.daily_range_text or self._build_range_text(
            weather_result.temp_min,
            weather_result.temp_max,
            weather_result.temperature_unit,
        )
        lines = [
            f"城市: {location_label}",
            f"坐标: {weather_result.lat}, {weather_result.lon}",
            f"当前温度: {weather_result.temperature}{weather_result.temperature_unit}",
            f"体感温度: {weather_result.feels_like}{weather_result.temperature_unit}",
        ]
        if range_line:
            lines.append(f"今日温度范围: {range_line}")
        if weather_result.observed_at_local:
            lines.append(f"天气数据时间: {weather_result.observed_at_local}")
        if weather_result.city_local_time:
            lines.append(f"城市当地时间: {weather_result.city_local_time}")
        lines.extend(
            [
                f"天气: {weather_result.description}",
                f"湿度: {weather_result.humidity}%",
                f"风速: {weather_result.wind_speed} {weather_result.wind_unit}",
                f"数据模式: {weather_result.data_mode}",
                f"数据来源: {weather_result.source}",
            ]
        )
        return "\n".join(lines)

    def get_weather(self, city_name: str) -> str:
        return self.format_weather(self.get_weather_by_query(city_name))

    def get_weather_details(self, city_name: str) -> dict[str, Any]:
        return self.get_weather_by_query(city_name).to_dict()


def get_weather(city_name: str, api_key: str | None = None, unit: str = "metric") -> str:
    weather = Weather(api_key=api_key, unit=unit)
    return weather.get_weather(city_name)


if __name__ == "__main__":
    weather = Weather()
    print(weather.get_weather("harbin"))
