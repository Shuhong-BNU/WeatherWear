from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.domain.types import LocationCandidate
from weatherwear.services import city_resolver
from weatherwear.services.city_resolver import resolve_city
from weatherwear.support.common_utils import stable_id


def make_candidate(
    city: str,
    state: str,
    country: str,
    country_code: str,
    lat: float,
    lon: float,
    confidence: float,
    source: str = "geocoding",
    query_text: str = "",
) -> LocationCandidate:
    return LocationCandidate(
        candidate_id=stable_id(city, state, country_code, str(lat), str(lon)),
        city=city,
        state=state,
        country=country,
        country_code=country_code,
        lat=lat,
        lon=lon,
        confidence=confidence,
        source=source,
        query_text=query_text or city,
        display_name=", ".join(part for part in [city, state, country] if part),
    )


class FakeWeatherService:
    def __init__(self):
        self.mapping = {
            "北京": [
                make_candidate("Beijing", "", "China", "CN", 39.9042, 116.4074, 0.95, query_text="北京"),
            ],
            "springfield": [
                make_candidate(
                    "Springfield",
                    "Missouri",
                    "United States",
                    "US",
                    37.2089,
                    -93.2923,
                    0.78,
                    query_text="springfield",
                ),
                make_candidate(
                    "Springfield",
                    "Illinois",
                    "United States",
                    "US",
                    39.7817,
                    -89.6501,
                    0.74,
                    query_text="springfield",
                ),
            ],
        }

    def validate_candidate(self, candidate: LocationCandidate) -> list[LocationCandidate]:
        return list(self.mapping.get(candidate.query_text or candidate.city, []))

    def geocode_city(self, query: str, limit: int = 6) -> list[LocationCandidate]:
        return list(self.mapping.get(query, []))[:limit]


class CityResolutionTests(unittest.TestCase):
    def setUp(self):
        city_resolver._CACHE.clear()
        self.weather_service = FakeWeatherService()

    def test_alias_city_resolves_without_clarification(self):
        result = resolve_city("北京", self.weather_service)
        self.assertEqual(result.resolution_status, "resolved")
        self.assertFalse(result.need_clarification)
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.selected.city, "Beijing")
        self.assertTrue(result.used_alias)

    def test_ambiguous_city_requires_clarification(self):
        result = resolve_city("springfield", self.weather_service)
        self.assertEqual(result.resolution_status, "needs_clarification")
        self.assertTrue(result.need_clarification)
        self.assertGreaterEqual(len(result.clarification_candidates), 2)

    def test_preferred_candidate_id_resolves_selected_option(self):
        first = resolve_city("springfield", self.weather_service)
        selected_id = first.clarification_candidates[1].candidate_id
        second = resolve_city("springfield", self.weather_service, preferred_candidate_id=selected_id)
        self.assertEqual(second.resolution_status, "resolved")
        self.assertFalse(second.need_clarification)
        self.assertEqual(second.selected_candidate_id, selected_id)

    def test_fast_mode_avoids_llm_when_direct_resolution_is_enough(self):
        with patch("weatherwear.services.city_resolver.run_agent", side_effect=AssertionError("should not call llm")):
            result = resolve_city("北京", self.weather_service, fast_mode=True)
        self.assertEqual(result.resolution_status, "resolved")
        self.assertFalse(result.used_llm)

    def test_strict_confirmation_mode_requires_manual_confirmation(self):
        result = resolve_city("北京", self.weather_service, confirmation_mode="strict")
        self.assertEqual(result.resolution_status, "needs_clarification")
        self.assertTrue(result.need_clarification)
        self.assertGreaterEqual(len(result.clarification_candidates), 1)
    def test_failed_resolution_is_not_cached(self):
        result = resolve_city("hailar", self.weather_service, fast_mode=True)
        self.assertEqual(result.resolution_status, "failed")

        self.weather_service.mapping["hailar"] = [
            make_candidate("Hailar", "Inner Mongolia", "China", "CN", 49.2389, 120.0229, 0.82, query_text="hailar"),
        ]
        retried = resolve_city("hailar", self.weather_service, fast_mode=True)
        self.assertEqual(retried.resolution_status, "resolved")
        self.assertIsNotNone(retried.selected)
        self.assertEqual(retried.selected.city, "Hailar")

    def test_single_degraded_candidate_resolves_without_manual_confirmation(self):
        degraded = make_candidate("海拉尔", "", "", "", 0.0, 0.0, 0.55, source="direct_geocoding", query_text="海拉尔")
        degraded.lat = None
        degraded.lon = None
        degraded.metadata["degraded_mode"] = True
        self.weather_service.mapping["海拉尔"] = [degraded]
        result = resolve_city("海拉尔", self.weather_service, fast_mode=True)
        self.assertEqual(result.resolution_status, "resolved")
        self.assertFalse(result.need_clarification)
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.selected.city, "海拉尔")


if __name__ == "__main__":
    unittest.main()
