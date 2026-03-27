from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import ANY, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

import weatherwear.api.server as api_server
from weatherwear.domain.types import CoordinatorResult, ExecutionRecord


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        api_server.app.dependency_overrides[api_server.require_developer_access] = lambda: None
        self.client = TestClient(api_server.app)

    def tearDown(self):
        api_server.app.dependency_overrides.clear()

    def test_examples_endpoint_returns_items(self):
        response = self.client.get("/api/examples")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("items", payload)
        self.assertTrue(payload["items"])

    def test_query_endpoint_supports_map_pin_mode(self):
        fake_result = CoordinatorResult(ok=True, user_input="1.35,103.82")
        fake_result.execution_trace = [
            ExecutionRecord(
                role="Map resolver",
                name="MapPinResolver",
                node_name="resolve_city",
                provider="reverse_geocoding",
                success=True,
                metadata={"lat": 1.35, "lon": 103.82},
            )
        ]
        fake_view_model = {
            "summary": {
                "request_id": "req-1",
                "user_input": "1.35,103.82",
                "selected_city": "Map Pin, Singapore",
                "confirmed_location_label": "Map Pin, Singapore",
                "resolution_status": "resolved",
                "resolution_confidence": 0.99,
                "models_used": [],
                "timezone_label": "UTC+08:00",
                "location_source": "map_pin",
                "confirmation_mode": "strict",
                "locale": "en-US",
                "selected_coords": {"lat": 1.35, "lon": 103.82},
            },
            "hero_summary": {"title": "Map Pin, Singapore", "query_path": "Fast path"},
            "weather": {"description": "Sunny"},
            "fashion": {"headline_advice": "Light layers."},
            "location_pin": {
                "lat": 1.35,
                "lon": 103.82,
                "label": "Map Pin, Singapore",
                "source": "map_pin",
                "confirmed": True,
                "zoom_hint": 10,
            },
            "clarification": {"needed": False, "recommended_candidate_id": "", "options": []},
            "trace": [],
            "debug_sections": {},
        }

        with patch.object(api_server, "record_runtime_event") as mock_events:
            with patch.object(api_server, "create_history_item") as mock_history:
                with patch.object(api_server.coordinator, "process_query", return_value=fake_result) as mock_process:
                    with patch.object(api_server, "build_result_view_model", return_value=fake_view_model) as mock_view:
                        response = self.client.post(
                            "/api/query",
                            json={
                                "query_text": "",
                                "confirmation_mode": "strict",
                                "selected_coords": {"lat": 1.35, "lon": 103.82},
                                "locale": "en-US",
                            },
                        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["view_model"]["summary"]["selected_city"], "Map Pin, Singapore")
        self.assertEqual(payload["view_model"]["location_pin"]["lat"], 1.35)
        mock_process.assert_called_once_with(
            "1.35,103.82",
            selected_candidate_id="",
            confirmation_mode="strict",
            selected_coords={"lat": 1.35, "lon": 103.82},
            location_source="map_pin",
            locale="en-US",
            gender="neutral",
            occasion_text="",
            target_date="",
            request_id=ANY,
        )
        mock_view.assert_called_once_with(fake_result, locale="en-US")
        mock_history.assert_called_once()
        event_types = [call.args[0] for call in mock_events.call_args_list]
        self.assertIn("query.started", event_types)
        self.assertIn("query.step", event_types)
        self.assertIn("query.completed", event_types)

    def test_health_endpoint_accepts_locale(self):
        with patch.object(api_server, "gather_runtime_health", return_value={"ok": True}) as mock_health:
            response = self.client.get("/api/health/runtime?locale=en-US")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        mock_health.assert_called_once_with("en-US")

    def test_developer_session_endpoints_are_wired(self):
        with patch.object(api_server, "get_developer_session_state", return_value={"required": True, "unlocked": False}) as mock_get:
            response = self.client.get("/api/dev/session")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["required"])
        mock_get.assert_called_once()

        with patch.object(api_server, "unlock_developer_access", return_value=True) as mock_unlock:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.post("/api/dev/unlock", json={"pin": "123456"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("set-cookie", response.headers)
        mock_unlock.assert_called_once_with("123456")

        with patch.object(api_server, "record_runtime_event"):
            response = self.client.post("/api/dev/lock")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["unlocked"])

    def test_model_settings_endpoints_are_wired(self):
        fake_settings = {
            "default_provider": "default",
            "providers": {
                "default": {
                    "name": "primary",
                    "provider": "openai_compatible",
                    "base_url": "https://example.com/v1",
                    "model": "gpt-4o-mini",
                    "proxy_url": "",
                    "temperature": 0.2,
                    "timeout_seconds": 60,
                    "enabled": True,
                    "missing_fields": [],
                    "has_api_key": True,
                },
                "alternate": {
                    "name": "backup",
                    "provider": "openai_compatible",
                    "base_url": "",
                    "model": "",
                    "proxy_url": "",
                    "temperature": 0.2,
                    "timeout_seconds": 60,
                    "enabled": False,
                    "missing_fields": ["ALT_LLM_API_KEY"],
                    "has_api_key": False,
                },
            },
            "embedding": {
                "enabled": False,
                "inherit_from_chat_provider": True,
                "provider": "openai_compatible",
                "base_url": "",
                "model": "",
                "proxy_url": "",
                "timeout_seconds": 60,
                "missing_fields": ["model"],
                "has_api_key": False,
            },
        }

        with patch.object(api_server, "build_model_settings_response", return_value=fake_settings) as mock_get:
            response = self.client.get("/api/settings/model")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["default_provider"], "default")
        mock_get.assert_called_once_with()

        with patch.object(api_server, "update_model_settings", return_value=fake_settings) as mock_update:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.put(
                    "/api/settings/model",
                    json={
                        "slot": "alternate",
                        "default_provider": "alternate",
                        "provider": {
                            "name": "backup",
                            "base_url": "https://alt.example/v1",
                            "model": "qwen-max",
                            "api_key": "secret",
                        },
                        "embedding": {
                            "enabled": True,
                            "inherit_from_chat_provider": False,
                            "provider": "openai_compatible",
                            "base_url": "https://embed.example/v1",
                            "model": "text-embedding-3-large",
                        },
                    },
                )
        self.assertEqual(response.status_code, 200)
        mock_update.assert_called_once_with(
            slot="alternate",
            payload={
                "name": "backup",
                "base_url": "https://alt.example/v1",
                "model": "qwen-max",
                "api_key": "secret",
                "embedding": {
                    "enabled": True,
                    "inherit_from_chat_provider": False,
                    "provider": "openai_compatible",
                    "base_url": "https://embed.example/v1",
                    "model": "text-embedding-3-large",
                },
                "default_provider": "alternate",
            },
            clear_api_key=False,
            clear_embedding_api_key=False,
        )

        with patch.object(
            api_server,
            "test_model_provider",
            return_value={
                "ok": True,
                "message": "connected",
                "provider": "openai_compatible",
                "model": "gpt-4o-mini",
                "latency_ms": 123,
            },
        ) as mock_test:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.post(
                    "/api/settings/model/test",
                    json={
                        "slot": "default",
                        "provider": {
                            "base_url": "https://example.com/v1",
                            "model": "gpt-4o-mini",
                        },
                    },
                )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mock_test.assert_called_once_with(
            slot="default",
            payload={"base_url": "https://example.com/v1", "model": "gpt-4o-mini"},
        )

    def test_map_settings_endpoints_are_wired(self):
        fake_settings = {
            "provider": "baidu",
            "baidu_ak": "ak-demo",
            "baidu_ak_configured": True,
            "osm_tile_url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "osm_attribution": "&copy;",
            "default_center_lat": 36.0,
            "default_center_lon": 120.0,
            "default_zoom": 9,
        }

        with patch.object(api_server, "build_map_settings_response", return_value=fake_settings) as mock_get:
            response = self.client.get("/api/settings/map")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "baidu")
        mock_get.assert_called_once_with()

        with patch.object(api_server, "update_map_settings", return_value=fake_settings) as mock_update:
            response = self.client.put("/api/settings/map", json={"provider": "baidu", "baidu_ak": "ak-demo"})
        self.assertEqual(response.status_code, 200)
        mock_update.assert_called_once()

        with patch.object(
            api_server,
            "test_map_settings",
            return_value={"ok": True, "message": "ready", "provider": "baidu"},
        ) as mock_test:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.post("/api/settings/map/test", json={"provider": "baidu", "baidu_ak": "ak-demo"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mock_test.assert_called_once()

    def test_history_favorites_and_logs_endpoints_are_wired(self):
        fake_history = [
            {
                "id": "h1",
                "created_at": "2026-03-22T12:00:00Z",
                "request_id": "req-1",
                "locale": "zh-CN",
                "query_text": "Qingdao",
                "confirmed_location_label": "Qingdao, China",
                "location_source": "text_search",
                "confirmation_mode": "smart",
                "query_path": "Fast path",
                "headline_advice": "Light layers",
                "weather_summary": "Sunny",
                "selected_coords": {"lat": 36.06, "lon": 120.38},
            }
        ]
        fake_favorites = [
            {
                "id": "f1",
                "label": "Qingdao, China",
                "lat": 36.06,
                "lon": 120.38,
                "source": "text_search",
                "query_text": "Qingdao",
                "added_at": "2026-03-22T12:10:00Z",
            }
        ]

        with patch.object(api_server, "list_history_items", return_value=fake_history):
            response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        with patch.object(api_server, "create_history_item", return_value=fake_history[0]) as mock_history_create:
            response = self.client.post("/api/history", json=fake_history[0] | {"selected_coords": {"lat": 36.06, "lon": 120.38}})
        self.assertEqual(response.status_code, 200)
        mock_history_create.assert_called_once()

        with patch.object(api_server, "delete_history_item", return_value=True) as mock_delete_history:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.delete("/api/history/h1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mock_delete_history.assert_called_once_with("h1")

        with patch.object(api_server, "list_favorite_items", return_value=fake_favorites):
            response = self.client.get("/api/favorites")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        with patch.object(api_server, "save_favorite_item", return_value=fake_favorites[0]) as mock_save_favorite:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.post("/api/favorites", json=fake_favorites[0])
        self.assertEqual(response.status_code, 200)
        mock_save_favorite.assert_called_once()

        with patch.object(api_server, "delete_favorite_item", return_value=True) as mock_delete_favorite:
            with patch.object(api_server, "record_runtime_event"):
                response = self.client.delete("/api/favorites/f1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mock_delete_favorite.assert_called_once_with("f1")

        with patch.object(
            api_server,
            "list_log_sources",
            return_value=[{"source": "app.events.jsonl", "label": "App Events", "kind": "structured", "size_bytes": 1, "updated_at": ""}],
        ) as mock_sources:
            response = self.client.get("/api/logs/sources")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["source"], "app.events.jsonl")

    def test_query_cancel_and_client_log_endpoints_are_wired(self):
        with patch.object(api_server.query_cancellation_registry, "cancel", return_value=True) as mock_cancel:
            with patch.object(api_server, "record_runtime_event") as mock_event:
                response = self.client.post("/api/query/cancel", json={"request_id": "req-cancel"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        mock_cancel.assert_called_once_with("req-cancel")
        self.assertEqual(mock_event.call_args.args[0], "query.cancel.requested")

        with patch.object(api_server, "record_runtime_event") as mock_event:
            response = self.client.post(
                "/api/logs/client-event",
                json={
                    "type": "frontend.map.baidu.error",
                    "message": "Baidu map runtime error captured.",
                    "level": "warning",
                    "payload": {"mapCreated": False},
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(mock_event.call_args.args[0], "frontend.map.baidu.error")

        with patch.object(
            api_server,
            "read_log_tail",
            return_value={"source": "app.events.jsonl", "kind": "structured", "lines": ["{}"], "events": [{"type": "query.started"}]},
        ) as mock_tail:
            response = self.client.get("/api/logs/tail?source=app.events.jsonl&lines=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["kind"], "structured")
        mock_tail.assert_called_once_with("app.events.jsonl", lines=10)


if __name__ == "__main__":
    unittest.main()
