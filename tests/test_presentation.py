from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.application.presentation import build_result_view_model
from weatherwear.domain.types import (
    CityResolutionResult,
    CoordinatorResult,
    FashionAdviceResult,
    KnowledgeHit,
    LocationCandidate,
    WeatherResult,
)
from weatherwear.support.common_utils import stable_id


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
            clarification_message="Need candidate confirmation.",
            clarification_candidates=[first, second],
        )

        view_model = build_result_view_model(result)
        self.assertEqual(view_model["clarification"]["recommended_candidate_id"], first.candidate_id)
        self.assertTrue(view_model["clarification"]["options"][0]["recommended"])

    def test_resolved_city_builds_headline_pin_and_knowledge_basis(self):
        selected = make_candidate("Qingdao", "Shandong", "China", "CN", 36.0671, 120.3826, 0.88)
        result = CoordinatorResult(user_input="青岛", location_source="text_search", locale="zh-CN")
        result.ok = True
        result.resolution = CityResolutionResult(
            raw_input="青岛",
            normalized_input="青岛",
            resolution_status="resolved",
            selected=selected,
            selected_candidate_id=selected.candidate_id,
            confidence=selected.confidence,
        )
        result.weather = WeatherResult(
            ok=True,
            city="Qingdao",
            state="Shandong",
            country="China",
            country_code="CN",
            lat=36.0671,
            lon=120.3826,
            temperature=9.0,
            feels_like=6.1,
            temp_min=7.5,
            temp_max=16.5,
            humidity=75,
            wind_speed=5.2,
            description="多云",
        )
        result.fashion = FashionAdviceResult(
            advice_text="### 今日建议\n全天偏凉，建议保暖内搭配轻外套。\n\n### 分时段建议\n- 早晨：加层。\n\n### 分层建议\n- 内层：保暖打底。",
            headline_advice="全天偏凉，建议保暖内搭配轻外套。",
            time_of_day_advice="- 早晨：加层。",
            layering_advice="- 内层：保暖打底。",
            source="rule_based_fashion",
            knowledge_hits=[
                KnowledgeHit(
                    knowledge_id="wide-range-layer",
                    label="昼夜温差大时准备可脱卸外层",
                    short_reason="温差命中较大，建议保留一层可增减的外层。",
                    summary="昼夜温差大时准备可脱卸外层",
                    body="日内温差明显时，建议保留可脱卸外层。",
                    score=0.66,
                )
            ],
        )

        view_model = build_result_view_model(result)
        self.assertEqual(view_model["fashion"]["headline_advice"], "全天偏凉，建议保暖内搭配轻外套。")
        self.assertEqual(view_model["hero_summary"]["one_line_advice"], "全天偏凉，建议保暖内搭配轻外套。")
        self.assertEqual(view_model["summary"]["confirmed_location_label"], "青岛，山东，中国")
        self.assertTrue(view_model["location_pin"]["confirmed"])
        self.assertEqual(view_model["location_pin"]["lat"], 36.0671)
        self.assertEqual(view_model["knowledge_basis"]["items"][0]["id"], "wide-range-layer")
        self.assertTrue(view_model["debug_sections"]["knowledge"])

    def test_map_query_uses_selected_coords_for_location_pin(self):
        result = CoordinatorResult(
            user_input="1.35,103.82",
            location_source="map_pin",
            selected_coords={"lat": 1.35, "lon": 103.82},
        )
        selected = make_candidate("Map Pin", "", "Singapore", "SG", 1.35, 103.82, 0.99)
        result.resolution = CityResolutionResult(
            raw_input="1.35,103.82",
            normalized_input="1.35,103.82",
            resolution_status="resolved",
            selected=selected,
            selected_candidate_id=selected.candidate_id,
            confidence=0.99,
        )

        view_model = build_result_view_model(result)
        self.assertEqual(view_model["location_pin"]["lat"], 1.35)
        self.assertEqual(view_model["location_pin"]["zoom_hint"], 10)

    def test_zh_locale_localizes_beijing_label(self):
        selected = make_candidate("Beijing", "Beijing", "China", "CN", 39.9042, 116.4074, 0.98)
        result = CoordinatorResult(user_input="北京", locale="zh-CN")
        result.ok = True
        result.resolution = CityResolutionResult(
            raw_input="北京",
            normalized_input="北京",
            resolution_status="resolved",
            selected=selected,
            selected_candidate_id=selected.candidate_id,
            confidence=selected.confidence,
        )
        result.weather = WeatherResult(
            ok=True,
            city="Beijing",
            state="Beijing",
            country="China",
            country_code="CN",
            lat=39.9042,
            lon=116.4074,
            description="多云",
        )

        view_model = build_result_view_model(result, locale="zh-CN")
        self.assertEqual(view_model["summary"]["confirmed_location_label"], "北京，中国")
        self.assertEqual(view_model["location_pin"]["label"], "北京，中国")


if __name__ == "__main__":
    unittest.main()
