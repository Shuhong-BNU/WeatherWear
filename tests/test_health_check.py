from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from health_check import RECOMMENDED_WEB_STACK, evaluate_web_stack, format_health_report


class HealthCheckTests(unittest.TestCase):
    def test_fastapi_version_mismatch_is_reported(self):
        web_stack = evaluate_web_stack(
            {
                "gradio": {"available": True, "version": RECOMMENDED_WEB_STACK["gradio"], "error": ""},
                "fastapi": {"available": False, "version": "0.135.1", "error": "TypeError: unsupported operand type(s) for |"},
                "pydantic": {"available": True, "version": RECOMMENDED_WEB_STACK["pydantic"], "error": ""},
                "typing_extensions": {"available": True, "version": RECOMMENDED_WEB_STACK["typing_extensions"], "error": ""},
                "huggingface_hub": {"available": True, "version": RECOMMENDED_WEB_STACK["huggingface_hub"], "error": ""},
            }
        )
        self.assertFalse(web_stack["compatible"])
        self.assertTrue(any("FastAPI" in item for item in web_stack["issues"]))

    def test_huggingface_hub_major_version_one_is_reported(self):
        web_stack = evaluate_web_stack(
            {
                "gradio": {"available": True, "version": RECOMMENDED_WEB_STACK["gradio"], "error": ""},
                "fastapi": {"available": True, "version": RECOMMENDED_WEB_STACK["fastapi"], "error": ""},
                "pydantic": {"available": True, "version": RECOMMENDED_WEB_STACK["pydantic"], "error": ""},
                "typing_extensions": {"available": True, "version": RECOMMENDED_WEB_STACK["typing_extensions"], "error": ""},
                "huggingface_hub": {"available": True, "version": "1.1.0", "error": ""},
            }
        )
        self.assertFalse(web_stack["compatible"])
        self.assertTrue(any("huggingface_hub" in item for item in web_stack["issues"]))

    def test_format_health_report_contains_recommended_matrix(self):
        report = format_health_report(
            {
                "python_version": "3.11.0",
                "platform": "test-platform",
                "llm_configured": False,
                "missing_llm_fields": ["LLM_API_KEY"],
                "openweather_configured": False,
                "modules": {
                    "gradio": {"available": True, "version": "4.44.1", "error": ""},
                    "fastapi": {"available": False, "version": "0.135.1", "error": "TypeError"},
                    "huggingface_hub": {"available": True, "version": RECOMMENDED_WEB_STACK["huggingface_hub"], "error": ""},
                },
                "web_stack": {
                    "compatible": False,
                    "issues": ["test issue"],
                    "recommended": dict(RECOMMENDED_WEB_STACK),
                },
                "suggestions": ["test suggestion"],
            }
        )
        self.assertIn("推荐 Web 依赖矩阵", report)
        self.assertIn("fastapi==0.112.2", report)
        self.assertIn("huggingface_hub==0.36.2", report)


if __name__ == "__main__":
    unittest.main()
