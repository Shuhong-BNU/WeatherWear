from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts import import_fashion_knowledge
from weatherwear.services.knowledge_admin import (
    default_retrieval_cases,
    evaluate_retrieval_cases,
    load_payloads_from_path,
    normalize_knowledge_payload,
    validate_knowledge_payloads,
)


class KnowledgeAdminTests(unittest.TestCase):
    @staticmethod
    def _make_fake_hit(knowledge_id: str, category: str) -> object:
        class _FakeHit:
            def __init__(self, knowledge_id: str, category: str) -> None:
                self.knowledge_id = knowledge_id
                self.category = category

            def to_dict(self) -> dict[str, str]:
                return {"knowledge_id": self.knowledge_id, "category": self.category}

        return _FakeHit(knowledge_id, category)

    def test_validate_knowledge_payloads_detects_invalid_entries(self):
        result = validate_knowledge_payloads(
            [
                {
                    "id": "",
                    "locale": "en-US",
                    "category": "bad_category",
                    "summary": "summary",
                    "body": "body",
                    "tags": ["ok"],
                    "occasion_hints": ["work"],
                    "gender_compatibility": ["neutral"],
                    "weather_conditions": [],
                    "structured_guidance": [],
                }
            ],
            locale="en-US",
        )

        issue_codes = {item["code"] for item in result["issues"]}
        self.assertFalse(result["ok"])
        self.assertIn("empty_id", issue_codes)
        self.assertIn("invalid_category", issue_codes)
        self.assertIn("invalid_weather_conditions", issue_codes)
        self.assertIn("invalid_structured_guidance", issue_codes)

    def test_normalize_knowledge_payload_trims_and_deduplicates(self):
        normalized = normalize_knowledge_payload(
            {
                "id": "  demo-id  ",
                "locale": " ",
                "category": " Upper_Body ",
                "summary": "  summary  ",
                "body": " body ",
                "tags": [" travel ", "", "travel", "Travel"],
                "occasion_hints": [" Work ", "", "work", "walking"],
                "gender_compatibility": [" Neutral ", "male", "male"],
                "weather_conditions": {" temperature_min ": 12, "condition_any": [" Rain ", "rain", " "]},
                "structured_guidance": {" notes ": [" keep dry ", "", "keep dry"]},
            },
            locale="en-US",
        )

        self.assertEqual(normalized["id"], "demo-id")
        self.assertEqual(normalized["locale"], "en-US")
        self.assertEqual(normalized["category"], "upper_body")
        self.assertEqual(normalized["tags"], ["travel", "Travel"])
        self.assertEqual(normalized["occasion_hints"], ["work", "walking"])
        self.assertEqual(normalized["gender_compatibility"], ["neutral", "male"])
        self.assertEqual(normalized["weather_conditions"], {"temperature_min": 12, "condition_any": ["rain"]})
        self.assertEqual(normalized["structured_guidance"], {"notes": ["keep dry"]})

    def test_validate_knowledge_payloads_reports_unknown_hints_and_duplicates(self):
        result = validate_knowledge_payloads(
            [
                {
                    "id": "demo-1",
                    "locale": "en-US",
                    "category": "upper_body",
                    "summary": "keep warm",
                    "body": "keep warm",
                    "tags": ["custom-tag"],
                    "occasion_hints": ["unknown-scene"],
                    "gender_compatibility": ["neutral"],
                    "weather_conditions": {"temperature_min": 10},
                    "structured_guidance": {"notes": ["alpha"]},
                },
                {
                    "id": "demo-2",
                    "locale": "en-US",
                    "category": "upper_body",
                    "summary": "keep warm",
                    "body": "keep warm",
                    "tags": ["custom-tag"],
                    "occasion_hints": ["unknown-scene"],
                    "gender_compatibility": ["neutral"],
                    "weather_conditions": {"temperature_min": 10},
                    "structured_guidance": {"notes": ["alpha"]},
                },
            ],
            locale="en-US",
        )

        issue_codes = {item["code"] for item in result["issues"]}
        self.assertTrue(result["ok"])
        self.assertIn("unknown_tag", issue_codes)
        self.assertIn("unknown_occasion_hint", issue_codes)
        self.assertIn("duplicate_summary_body", issue_codes)
        self.assertIn("duplicate_entry_signature", issue_codes)

    def test_evaluate_retrieval_cases_reports_expectation_summary(self):
        fake_hits = [
            self._make_fake_hit("demo-top", "upper_body"),
            self._make_fake_hit("demo-second", "bottoms"),
        ]
        fake_records = [
            SimpleNamespace(node_name="retrieve_knowledge_rules", metadata={"hits": [{"id": "demo-top", "score": 0.9}]}),
            SimpleNamespace(node_name="retrieve_knowledge_vector", metadata={"vector_leg_status": "skipped", "hits": []}),
            SimpleNamespace(node_name="rerank_knowledge", metadata={"retrieval_mode": "rules_only"}),
        ]

        with patch("weatherwear.services.knowledge_admin.knowledge.retrieve_knowledge_hits", return_value=(fake_hits, fake_records)):
            result = evaluate_retrieval_cases(
                [
                    {
                        "name": "demo_case",
                        "locale": "en-US",
                        "weather": {
                            "temperature": 20,
                            "feels_like": 20,
                            "temp_min": 18,
                            "temp_max": 22,
                            "description": "Clear",
                            "humidity": 40,
                            "wind_speed": 1.0,
                        },
                        "query_context": {"query_text": "demo"},
                        "expected_any_hit_ids": ["demo-top"],
                        "expected_top_hit_ids": ["demo-top"],
                        "expected_retrieval_mode": "rules_only",
                        "expected_vector_leg_status": "skipped",
                    }
                ]
            )

        self.assertEqual(result["case_count"], 1)
        self.assertEqual(result["checked_case_count"], 1)
        self.assertEqual(result["passed_case_count"], 1)
        self.assertEqual(result["failed_case_count"], 0)
        self.assertEqual(result["check_count"], 4)
        self.assertEqual(result["failed_check_count"], 0)
        self.assertTrue(result["cases"][0]["passed"])

    def test_import_script_writes_normalized_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            input_path = temp_root / "incoming.json"
            output_path = temp_root / "out.jsonl"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "id": " demo-import ",
                            "locale": "en-US",
                            "category": "UPPER_BODY",
                            "summary": "summary",
                            "body": "body",
                            "tags": ["travel", "travel"],
                            "occasion_hints": ["work", "work"],
                            "gender_compatibility": ["neutral", "neutral"],
                            "weather_conditions": {"temperature_max": 18},
                            "structured_guidance": {"notes": ["packable", "packable"]},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            argv_backup = sys.argv[:]
            try:
                sys.argv = [
                    "import_fashion_knowledge.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ]
                with redirect_stdout(StringIO()):
                    exit_code = import_fashion_knowledge.main()
            finally:
                sys.argv = argv_backup

            self.assertEqual(exit_code, 0)
            payloads = load_payloads_from_path(output_path)
            self.assertEqual(len(payloads), 1)
            self.assertEqual(payloads[0]["id"], "demo-import")
            self.assertEqual(payloads[0]["category"], "upper_body")
            self.assertEqual(payloads[0]["occasion_hints"], ["work"])
            self.assertEqual(payloads[0]["structured_guidance"], {"notes": ["packable"]})

    def test_default_retrieval_cases_include_bilingual_pairs(self):
        cases = default_retrieval_cases()

        self.assertEqual(len(cases), 6)
        self.assertEqual({case["locale"] for case in cases}, {"en-US", "zh-CN"})
        self.assertTrue(all(case.get("expected_retrieval_mode") == "rules_only" for case in cases))
        self.assertTrue(all(case.get("expected_vector_leg_status") == "skipped" for case in cases))
        self.assertTrue(any(case["name"].endswith("_en") for case in cases))
        self.assertTrue(any(case["name"].endswith("_zh") for case in cases))


if __name__ == "__main__":
    unittest.main()
