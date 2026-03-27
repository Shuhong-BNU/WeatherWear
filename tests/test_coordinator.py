from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.domain.types import ExecutionRecord, FashionAdviceResult, QueryPlan, WeatherResult
from weatherwear.application.coordinator import MultiAgentCoordinator


class CoordinatorExecutionTests(unittest.TestCase):
    def test_plan_steps_drive_execution_order(self):
        coordinator = MultiAgentCoordinator()
        calls: list[str] = []

        def fake_plan_query(user_input, request_id):
            return (
                QueryPlan(
                    intent="weather_and_fashion",
                    raw_location=user_input,
                    need_resolution=True,
                    steps=["resolve_city", "fetch_weather"],
                    fallback_policy=["alias_lookup"],
                    source="test_plan",
                ),
                ExecutionRecord(role="planner", name="planner", success=True, request_id=request_id),
            )

        coordinator.plan_query = fake_plan_query
        coordinator._should_use_planner = lambda user_input, selected_candidate_id="": True
        coordinator._run_resolution_step = lambda result, preferred_candidate_id="": calls.append("resolve_city") or True
        coordinator._run_weather_step = lambda result: calls.append("fetch_weather") or True
        coordinator._run_fashion_step = lambda result: calls.append("generate_outfit") or True
        coordinator._finalize_warnings = lambda result, plan_record: None

        coordinator.process_query("beijing")
        self.assertEqual(calls, ["resolve_city", "fetch_weather"])

    def test_clarification_stops_following_steps(self):
        coordinator = MultiAgentCoordinator()
        calls: list[str] = []

        def fake_plan_query(user_input, request_id):
            return (
                QueryPlan(
                    intent="weather_and_fashion",
                    raw_location=user_input,
                    need_resolution=True,
                    steps=["resolve_city", "fetch_weather", "generate_outfit"],
                    fallback_policy=["alias_lookup"],
                    source="test_plan",
                ),
                ExecutionRecord(role="planner", name="planner", success=True, request_id=request_id),
            )

        def fake_resolution(result, preferred_candidate_id=""):
            calls.append("resolve_city")
            result.resolution.need_clarification = True
            result.resolution.resolution_status = "needs_clarification"
            result.resolution.clarification_message = "需要确认候选城市"
            return False

        coordinator.plan_query = fake_plan_query
        coordinator._should_use_planner = lambda user_input, selected_candidate_id="": True
        coordinator._run_resolution_step = fake_resolution
        coordinator._run_weather_step = lambda result: calls.append("fetch_weather") or True
        coordinator._run_fashion_step = lambda result: calls.append("generate_outfit") or True
        coordinator._finalize_warnings = lambda result, plan_record: None

        result = coordinator.process_query("springfield")
        self.assertEqual(calls, ["resolve_city"])
        self.assertFalse(result.ok)

    def test_simple_city_uses_fast_path_without_planner(self):
        coordinator = MultiAgentCoordinator()
        calls: list[str] = []

        def fail_plan_query(user_input, request_id):
            raise AssertionError("simple city should not use planner")

        coordinator.plan_query = fail_plan_query
        coordinator._run_resolution_step = lambda result, preferred_candidate_id="": calls.append("resolve_city") or True
        coordinator._run_weather_step = lambda result: calls.append("fetch_weather") or True
        coordinator._run_fashion_step = lambda result: calls.append("generate_outfit") or True
        coordinator._finalize_warnings = lambda result, plan_record: None

        result = coordinator.process_query("beijing")
        self.assertTrue(result.used_fast_path)
        self.assertEqual(calls, ["resolve_city", "fetch_weather", "generate_outfit"])

    def test_trace_contains_graph_runtime_and_provider_metadata(self):
        coordinator = MultiAgentCoordinator()
        coordinator._finalize_warnings = lambda result, plan_record: None

        def fake_resolution(result, preferred_candidate_id=""):
            result.resolution.resolution_status = "resolved"
            return True

        def fake_weather(result):
            result.weather = WeatherResult(ok=True, data_mode="demo", source="demo_weather")
            return True

        def fake_fashion(result):
            result.fashion = FashionAdviceResult(advice_text="ok", source="rule_based_fashion")
            return True

        coordinator._run_resolution_step = fake_resolution
        coordinator._run_weather_step = fake_weather
        coordinator._run_fashion_step = fake_fashion

        result = coordinator.process_query("beijing")
        self.assertIn(result.graph_runtime, {"compat_state_graph", "langgraph"})
        self.assertTrue(result.execution_trace)
        self.assertEqual(result.execution_trace[0].node_name, "planner")
        self.assertTrue(result.execution_trace[0].provider)

    def test_cancellation_marks_result_and_stops_following_steps(self):
        coordinator = MultiAgentCoordinator()
        coordinator._finalize_warnings = lambda result, plan_record: None

        def fake_resolution(result, preferred_candidate_id="", cancel_token=None):
            result.resolution.resolution_status = "resolved"
            result.resolution.selected = object()
            return True

        def fake_weather(result, cancel_token=None):
            if cancel_token is not None:
                cancel_token.registry.cancel(cancel_token.request_id)
            return True

        def fake_fashion(result, cancel_token=None):
            raise AssertionError("fashion step should not run after cancellation")

        coordinator._run_resolution_step = fake_resolution
        coordinator._run_weather_step = fake_weather
        coordinator._run_fashion_step = fake_fashion

        result = coordinator.process_query("beijing")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "query_cancelled")
        self.assertEqual(result.execution_trace[-1].node_name, "cancel_query")


if __name__ == "__main__":
    unittest.main()
