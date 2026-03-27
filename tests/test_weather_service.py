from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.domain.types import LocationCandidate
from weatherwear.support.common_utils import stable_id
from weatherwear.services.weather_service import Weather


class StubWeather(Weather):
    def __init__(self, responses):
        super().__init__(api_key="test-key")
        self.responses = list(responses)

    def _request_json(self, url, params, *, cache_key, ttl_seconds):  # noqa: D401
        if not self.responses:
            return None, "no_stub_response"
        return self.responses.pop(0)


class KeyFailureWeather(Weather):
    def __init__(self):
        super().__init__(api_key="bad-key")

    def _request_json(self, url, params, *, cache_key, ttl_seconds):  # noqa: D401
        return None, "HTTP 401: Invalid API key"


def make_location(city: str, state: str, country: str, country_code: str, lat: float, lon: float) -> LocationCandidate:
    return LocationCandidate(
        candidate_id=stable_id(city, state, country_code, str(lat), str(lon)),
        city=city,
        state=state,
        country=country,
        country_code=country_code,
        lat=lat,
        lon=lon,
        confidence=0.95,
        source="test",
        query_text=city,
        display_name=", ".join(part for part in [city, state, country] if part),
    )


class WeatherServiceTests(unittest.TestCase):
    def test_demo_mode_known_alias_returns_demo_weather(self):
        service = Weather(api_key="")
        result = service.get_weather_by_query("北京")
        self.assertTrue(result.ok)
        self.assertEqual(result.data_mode, "demo")
        self.assertTrue(result.demo_mode)

    def test_demo_mode_unknown_city_returns_demo_weather(self):
        service = Weather(api_key="")
        result = service.get_weather_by_query("unknown-city-for-test")
        self.assertTrue(result.ok)
        self.assertEqual(result.data_mode, "demo")

    def test_invalid_api_key_geocoding_degrades_to_demo_candidate(self):
        service = KeyFailureWeather()
        candidates = service.geocode_city("海拉尔")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].city, "海拉尔")
        self.assertEqual(candidates[0].source, "geocoding_fallback")

    def test_invalid_api_key_future_date_returns_demo_forecast(self):
        service = KeyFailureWeather()
        location = make_location("Hailar", "Inner Mongolia", "China", "CN", 49.2389, 120.0229)
        result = service.get_weather_for_candidate_on_date(location, target_date="2026-03-26")
        self.assertTrue(result.ok)
        self.assertTrue(result.demo_mode)
        self.assertTrue(result.is_forecast)
        self.assertEqual(result.forecast_mode, "forecast_day")
        self.assertEqual(result.forecast_date, "2026-03-26")
        self.assertIn("401", result.error)

    def test_demo_weather_changes_with_target_date(self):
        service = Weather(api_key="")
        location = make_location("Singapore", "", "Singapore", "SG", 1.3521, 103.8198)
        day_one = service.get_weather_for_candidate_on_date(location, target_date="2026-03-28")
        day_two = service.get_weather_for_candidate_on_date(location, target_date="2026-03-29")
        self.assertTrue(day_one.ok)
        self.assertTrue(day_two.ok)
        self.assertNotEqual(
            (day_one.temperature, day_one.temp_min, day_one.temp_max, day_one.description),
            (day_two.temperature, day_two.temp_min, day_two.temp_max, day_two.description),
        )

    def test_latlon_failure_can_fallback_to_q_mode(self):
        service = StubWeather(
            responses=[
                (None, "latlon boom"),
                (
                    {
                        "name": "Paris",
                        "weather": [{"description": "晴"}],
                        "main": {"temp": 24.0, "feels_like": 25.0, "humidity": 61},
                        "wind": {"speed": 2.2},
                        "sys": {"country": "FR"},
                        "coord": {"lat": 48.8566, "lon": 2.3522},
                    },
                    "",
                ),
            ]
        )
        location = make_location("Paris", "Ile-de-France", "France", "FR", 48.8566, 2.3522)
        result = service.get_weather_for_candidate(location, allow_q_fallback=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.data_mode, "real_q_fallback")
        self.assertEqual(result.error, "latlon boom")
        self.assertTrue(result.fallback_used)

    def test_latlon_failure_without_q_fallback_returns_error(self):
        service = StubWeather(responses=[(None, "latlon boom")])
        location = make_location("Paris", "Ile-de-France", "France", "FR", 48.8566, 2.3522)
        result = service.get_weather_by_coords(
            48.8566,
            2.3522,
            location=location,
            allow_q_fallback=False,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.data_mode, "error")
        self.assertEqual(result.source, "openweather_latlon")

    def test_success_result_contains_time_and_daily_range(self):
        service = StubWeather(
            responses=[
                (
                    {
                        "name": "Paris",
                        "weather": [{"description": "晴"}],
                        "main": {
                            "temp": 24.0,
                            "feels_like": 25.0,
                            "temp_min": 20.0,
                            "temp_max": 26.0,
                            "humidity": 61,
                        },
                        "wind": {"speed": 2.2},
                        "sys": {"country": "FR"},
                        "coord": {"lat": 48.8566, "lon": 2.3522},
                        "dt": 1711000000,
                        "timezone": 3600,
                    },
                    "",
                ),
                (
                    {
                        "city": {"timezone": 3600},
                        "list": [
                            {"dt": 1711000000, "main": {"temp_min": 19.0, "temp_max": 25.0}},
                            {"dt": 1711010800, "main": {"temp_min": 18.0, "temp_max": 27.0}},
                        ],
                    },
                    "",
                ),
            ]
        )
        location = make_location("Paris", "Ile-de-France", "France", "FR", 48.8566, 2.3522)
        result = service.get_weather_for_candidate(location)
        self.assertTrue(result.ok)
        self.assertEqual(result.temp_min, 18.0)
        self.assertEqual(result.temp_max, 27.0)
        self.assertTrue(result.daily_range_text)
        self.assertTrue(result.observed_at)
        self.assertTrue(result.observed_at_local)
        self.assertTrue(result.city_local_time)
        self.assertGreaterEqual(result.request_elapsed_ms, 0)


if __name__ == "__main__":
    unittest.main()
