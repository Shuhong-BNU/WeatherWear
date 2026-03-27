from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.domain.types import WeatherResult
from weatherwear.services.fashion_knowledge import retrieve_knowledge_hits


class FashionKnowledgeTests(unittest.TestCase):
    def test_rules_only_retrieval_marks_vector_leg_as_skipped(self):
        weather = WeatherResult(
            ok=True,
            city="Beijing",
            country="China",
            temperature=8,
            feels_like=6,
            temp_min=5,
            temp_max=10,
            description="Clear",
            humidity=35,
            wind_speed=2.1,
        )

        with patch(
            "weatherwear.services.fashion_knowledge.get_embedding_config",
            return_value={"enabled": False},
        ):
            hits, records = retrieve_knowledge_hits(
                weather,
                locale="en-US",
                query_context={
                    "query_text": "Beijing outfit advice",
                    "occasion_text": "work commute",
                    "occasion_tags": ["work"],
                    "primary_scene": "work",
                    "gender": "neutral",
                },
            )

        self.assertTrue(hits)
        vector_record = next(record for record in records if record.node_name == "retrieve_knowledge_vector")
        rerank_record = next(record for record in records if record.node_name == "rerank_knowledge")
        self.assertEqual(vector_record.metadata.get("vector_leg_status"), "skipped")
        self.assertEqual(rerank_record.metadata.get("retrieval_mode"), "rules_only")

    def test_vector_retrieval_falls_back_to_local_cache_when_chroma_is_unavailable(self):
        weather = WeatherResult(
            ok=True,
            city="Beijing",
            country="China",
            temperature=14,
            feels_like=12,
            temp_min=10,
            temp_max=18,
            description="Clear",
            humidity=42,
            wind_speed=3.2,
        )

        def fake_embed_texts(texts, payload=None):
            vectors = []
            for index, text in enumerate(texts, start=1):
                size = float(len(text) % 7 + index)
                vectors.append([size, size / 2, size / 3])
            return vectors, {"ok": True, "provider": "mock-embedding", "model": "mock-vector"}

        fake_cache = {
            "metadata": {"embedding_dim": 3},
            "items": [
                {"id": "work-cold-upper", "embedding": [0.8, 0.4, 0.2]},
                {"id": "work-cold-bottoms", "embedding": [0.7, 0.35, 0.18]},
            ],
        }

        with patch(
            "weatherwear.services.fashion_knowledge._ensure_vector_collection",
            return_value=(None, {"ok": False, "error": "chromadb_missing:test", "fallback_used": True}),
        ):
            with patch(
                "weatherwear.services.fashion_knowledge._ensure_vector_cache",
                return_value=(fake_cache, {"ok": True, "provider": "json_vector_cache", "index": {"embedding_dim": 3}}),
            ):
                with patch("weatherwear.services.fashion_knowledge.embed_texts", side_effect=fake_embed_texts):
                    with patch(
                        "weatherwear.services.fashion_knowledge.get_embedding_config",
                        return_value={"enabled": True, "model": "mock-vector"},
                    ):
                        hits, records = retrieve_knowledge_hits(
                            weather,
                            locale="en-US",
                            query_context={
                                "query_text": "Beijing outfit advice",
                                "occasion_text": "work commute with office AC",
                                "occasion_tags": ["work", "air_conditioning"],
                                "gender": "neutral",
                            },
                        )

        self.assertTrue(hits)
        self.assertTrue(
            any(
                record.node_name == "retrieve_knowledge_vector" and record.provider == "json_vector_cache"
                for record in records
            )
        )

    def test_hybrid_rerank_combines_rule_and_vector_hits(self):
        weather = WeatherResult(
            ok=True,
            city="Beijing",
            country="China",
            temperature=12,
            feels_like=10,
            temp_min=9,
            temp_max=16,
            description="Cloudy",
            humidity=48,
            wind_speed=2.8,
        )

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                return {
                    "ids": [["work-cold-upper", "work-cold-bottoms"]],
                    "distances": [[0.12, 0.26]],
                }

        with patch(
            "weatherwear.services.fashion_knowledge._ensure_vector_collection",
            return_value=(FakeCollection(), {"ok": True, "provider": "chroma", "index": {"embedding_dim": 3}}),
        ):
            with patch(
                "weatherwear.services.fashion_knowledge.embed_texts",
                return_value=([[0.1, 0.2, 0.3]], {"ok": True, "provider": "mock", "model": "mock", "dimensions": 3}),
            ):
                hits, records = retrieve_knowledge_hits(
                    weather,
                    locale="en-US",
                    query_context={
                        "query_text": "Beijing outfit advice",
                        "occasion_text": "work commute with office AC",
                        "occasion_tags": ["work", "office"],
                        "primary_scene": "work",
                        "gender": "neutral",
                    },
                )

        self.assertTrue(hits)
        vector_record = next(record for record in records if record.node_name == "retrieve_knowledge_vector")
        rerank_record = next(record for record in records if record.node_name == "rerank_knowledge")
        self.assertEqual(vector_record.provider, "chroma")
        self.assertEqual(rerank_record.metadata.get("retrieval_mode"), "hybrid")
        self.assertGreater(rerank_record.metadata.get("vector_hit_count", 0), 0)


if __name__ == "__main__":
    unittest.main()
