from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.support.health_check import RECOMMENDED_WEB_STACK, evaluate_web_stack, format_health_report


class HealthCheckTests(unittest.TestCase):
    def test_fastapi_version_mismatch_is_reported(self):
        web_stack = evaluate_web_stack(
            {
                "fastapi": {"available": False, "version": "0.135.1", "error": "TypeError: unsupported operand type(s) for |"},
                "pydantic": {"available": True, "version": RECOMMENDED_WEB_STACK["pydantic"], "error": ""},
                "typing_extensions": {"available": True, "version": RECOMMENDED_WEB_STACK["typing_extensions"], "error": ""},
                "requests": {"available": True, "version": RECOMMENDED_WEB_STACK["requests"], "error": ""},
            }
        )
        self.assertFalse(web_stack["compatible"])
        self.assertTrue(any("FastAPI" in item for item in web_stack["issues"]))

    def test_requests_version_mismatch_is_reported(self):
        web_stack = evaluate_web_stack(
            {
                "fastapi": {"available": True, "version": RECOMMENDED_WEB_STACK["fastapi"], "error": ""},
                "pydantic": {"available": True, "version": RECOMMENDED_WEB_STACK["pydantic"], "error": ""},
                "typing_extensions": {"available": True, "version": RECOMMENDED_WEB_STACK["typing_extensions"], "error": ""},
                "requests": {"available": True, "version": "2.31.0", "error": ""},
            }
        )
        self.assertTrue(any("requests" in item for item in web_stack["issues"]))

    def test_format_health_report_contains_recommended_matrix(self):
        report = format_health_report(
            {
                "python_version": "3.11.0",
                "platform": "test-platform",
                "llm_configured": False,
                "missing_llm_fields": ["LLM_API_KEY"],
                "openweather_configured": False,
                "modules": {
                    "fastapi": {"available": False, "version": "0.135.1", "error": "TypeError"},
                    "requests": {"available": True, "version": RECOMMENDED_WEB_STACK["requests"], "error": ""},
                },
                "web_stack": {
                    "compatible": False,
                    "issues": ["test issue"],
                    "recommended": dict(RECOMMENDED_WEB_STACK),
                },
                "suggestions": ["test suggestion"],
            }
        )
        self.assertIn("推荐运行时依赖矩阵", report)
        self.assertIn("fastapi==0.112.2", report)
        self.assertIn("requests==2.32.5", report)


if __name__ == "__main__":
    unittest.main()
