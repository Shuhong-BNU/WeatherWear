from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_types import CityResolutionResult, CoordinatorResult, LocationCandidate
from common_utils import stable_id
from presentation import build_result_view_model


def make_candidate(city: str, state: str, country: str, country_code: str, lat: float, lon: float, confidence: float):
    return LocationCandidate(
        candidate_id=stable_id(city, state, country_code, str(lat), str(lon)),
        city=city,
        state=state,
        country=country,
        country_code=country_code,
        lat=lat,
        lon=lon,
        confidence=confidence,
        source="direct_geocoding",
        query_text=city,
        display_name=", ".join(part for part in [city, state, country] if part),
        metadata={"matched_query": city},
    )


class PresentationTests(unittest.TestCase):
    def test_clarification_contains_recommended_candidate(self):
        first = make_candidate("Springfield", "Missouri", "United States", "US", 37.20, -93.29, 0.78)
        second = make_candidate("Springfield", "Illinois", "United States", "US", 39.78, -89.65, 0.74)
        result = CoordinatorResult(user_input="springfield")
        result.resolution = CityResolutionResult(
            raw_input="springfield",
            normalized_input="springfield",
            resolution_status="needs_clarification",
            need_clarification=True,
            clarification_message="需要确认候选城市",
            clarification_candidates=[first, second],
        )

        view_model = build_result_view_model(result)
        self.assertEqual(view_model["clarification"]["recommended_candidate_id"], first.candidate_id)
        self.assertTrue(view_model["clarification"]["options"][0]["recommended"])
        self.assertIn("综合评分最高", view_model["clarification"]["options"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
