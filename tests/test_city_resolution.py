from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_types import LocationCandidate
from city_resolver import resolve_city
from common_utils import stable_id


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
                make_candidate("Springfield", "Missouri", "United States", "US", 37.2089, -93.2923, 0.78, query_text="springfield"),
                make_candidate("Springfield", "Illinois", "United States", "US", 39.7817, -89.6501, 0.74, query_text="springfield"),
            ],
        }

    def validate_candidate(self, candidate: LocationCandidate) -> list[LocationCandidate]:
        return list(self.mapping.get(candidate.query_text or candidate.city, []))

    def geocode_city(self, query: str, limit: int = 6) -> list[LocationCandidate]:
        return list(self.mapping.get(query, []))[:limit]


class CityResolutionTests(unittest.TestCase):
    def setUp(self):
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
        with patch("city_resolver.run_agent", side_effect=AssertionError("should not call llm")):
            result = resolve_city("北京", self.weather_service, fast_mode=True)
        self.assertEqual(result.resolution_status, "resolved")
        self.assertFalse(result.used_llm)


if __name__ == "__main__":
    unittest.main()
