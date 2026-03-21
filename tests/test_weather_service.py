from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_types import LocationCandidate
from common_utils import stable_id
from weather import Weather


class StubWeather(Weather):
    def __init__(self, responses):
        super().__init__(api_key="test-key")
        self.responses = list(responses)

    def _request_json(self, url, params, *, cache_key, ttl_seconds):  # noqa: D401
        if not self.responses:
            return None, "no_stub_response"
        return self.responses.pop(0)


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

    def test_demo_mode_unknown_city_returns_error_not_demo(self):
        service = Weather(api_key="")
        result = service.get_weather_by_query("unknown-city-for-test")
        self.assertFalse(result.ok)
        self.assertEqual(result.data_mode, "error")

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
