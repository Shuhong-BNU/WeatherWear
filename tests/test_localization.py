from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.support.localization import localize_location_label, localize_weather_description


class LocalizationTests(unittest.TestCase):
    def test_zh_locale_localizes_qingzhou_label(self):
        label = localize_location_label("Qingzhou City", "Shandong", "China", "CN", "zh-CN")
        self.assertEqual(label, "青州，山东，中国")

    def test_zh_locale_localizes_ilha_verde_label(self):
        label = localize_location_label("Ilha Verde", "Macau", "China", "CN", "zh-CN")
        self.assertEqual(label, "青洲，澳门，中国")

    def test_en_locale_normalizes_mixed_city_name(self):
        label = localize_location_label("青洲 Ilha Verde", "Macau", "China", "CN", "en-US")
        self.assertEqual(label, "Ilha Verde, Macau, China")

    def test_weather_description_localizes_to_english(self):
        self.assertEqual(localize_weather_description("晴，少云", "en-US"), "Clear, few clouds")

    def test_weather_description_localizes_to_chinese(self):
        self.assertEqual(localize_weather_description("few clouds", "zh-CN"), "少云")


if __name__ == "__main__":
    unittest.main()
