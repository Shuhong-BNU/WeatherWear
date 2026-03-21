from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fashion_agent import FashionAgent
from app_types import WeatherResult


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
        self.assertIn("### 分时段建议", result.advice_text)
        self.assertIn("### 分层建议", result.advice_text)
        self.assertIn("早晨", result.time_of_day_advice)
        self.assertIn("内层", result.layering_advice)
        self.assertFalse(result.used_llm)


if __name__ == "__main__":
    unittest.main()
