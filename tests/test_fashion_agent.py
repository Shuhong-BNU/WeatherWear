from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.domain.types import ExecutionRecord, WeatherResult
from weatherwear.services.fashion_agent import FashionAgent


class FashionAgentTests(unittest.TestCase):
    def test_rule_based_advice_contains_time_and_layer_sections(self):
        agent = FashionAgent()
        weather = WeatherResult(
            ok=True,
            city="Beijing",
            country="China",
            temperature=12,
            feels_like=10,
            temp_min=4,
            temp_max=18,
            daily_range_text="4°C ~ 18°C",
            description="多云",
            humidity=55,
            wind_speed=3.5,
        )
        result = agent.get_rule_based_fashion_advice(weather)
        self.assertIn("###", result.advice_text)
        self.assertTrue(result.headline_advice)
        self.assertIn("早晨", result.time_of_day_advice)
        self.assertIn("内层", result.layering_advice)
        self.assertFalse(result.used_llm)

    def test_fashion_advice_exposes_knowledge_hits_even_on_fallback(self):
        agent = FashionAgent()
        weather = WeatherResult(
            ok=True,
            city="Qingdao",
            country="China",
            temperature=9,
            feels_like=6,
            temp_min=7,
            temp_max=18,
            daily_range_text="7°C ~ 18°C",
            description="小雨",
            humidity=86,
            wind_speed=6.2,
        )

        result = agent.get_fashion_advice(weather, query_context="通勤去上班")

        self.assertTrue(result.knowledge_hits)
        self.assertLessEqual(len(result.knowledge_hits), 5)
        self.assertTrue(
            any(
                record.node_name in {"retrieve_knowledge_rules", "retrieve_knowledge_vector", "rerank_knowledge"}
                for record in result.execution_records
            )
        )

    def test_english_locale_falls_back_when_llm_returns_chinese(self):
        agent = FashionAgent()
        weather = WeatherResult(
            ok=True,
            city="Beijing",
            country="China",
            temperature=16,
            feels_like=15,
            temp_min=12,
            temp_max=18,
            daily_range_text="12°C ~ 18°C",
            description="Cloudy",
            humidity=40,
            wind_speed=3.7,
        )

        with patch(
            "weatherwear.services.fashion_agent.run_agent",
            return_value=("### 今日建议\n今天偏凉。", ExecutionRecord(role="test", name="FashionAgent", success=True)),
        ):
            result = agent.get_fashion_advice(weather, locale="en-US", query_context="commute")

        self.assertFalse(result.used_llm)
        self.assertTrue(result.fallback_used)
        self.assertIn("Morning", result.time_of_day_advice)


if __name__ == "__main__":
    unittest.main()
