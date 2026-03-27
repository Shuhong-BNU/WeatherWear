from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.validate_project import build_validation_summary


class ValidateProjectTests(unittest.TestCase):
    def test_build_validation_summary_includes_labels_and_next_action(self):
        summary = build_validation_summary(
            [
                {"name": "core_python_tests", "ok": True},
                {"name": "knowledge_validation", "ok": False},
            ],
            report_path=Path(".runtime") / "validation-report.json",
        )

        self.assertEqual(summary["headline"], "Validation failed (1 of 2 steps)")
        self.assertEqual(summary["report_path"], ".runtime/validation-report.json")
        self.assertEqual(summary["items"][0]["label"], "Core Python tests")
        self.assertEqual(summary["items"][1]["status"], "FAIL")
        self.assertIn("schema or locale alignment issues", summary["next_action"])


if __name__ == "__main__":
    unittest.main()
