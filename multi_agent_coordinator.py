from __future__ import annotations

import json
import time
from datetime import datetime

from app_types import CoordinatorResult, ExecutionRecord, QueryPlan, QueryState, WeatherResult
from city_resolver import resolve_city
from common_utils import compact_text, extract_probable_location, is_complex_weather_query
from fashion_agent import FashionAgent
from health_check import gather_runtime_health
from llm_support import extract_json_payload, run_agent
from observability import log_event, metrics_snapshot, new_request_id, record_metric
from weather import Weather
from workflow_graph import run_query_workflow


COORDINATOR_SYSTEM_PROMPT = """你是多智能体天气穿搭系统中的 Supervisor。
你的任务不是直接回答天气或穿搭，而是输出一个严格的 JSON 执行计划。

输出必须是 JSON，格式如下：
{
  "intent": "weather_and_fashion",
  "raw_location": "用户真正想查询的地点",
  "need_resolution": true,
  "need_clarification": false,
  "steps": ["resolve_city", "fetch_weather", "generate_outfit"],
  "fallback_policy": ["alias_lookup", "llm_city_resolution", "direct_geocoding", "q_weather_fallback", "rule_based_fashion"]
}

规则：
1. 只输出 JSON，不要输出解释。
2. raw_location 只保留地点本身，不要保留“查询”“天气”“穿搭建议”等额外描述。
3. 默认 intent 为 weather_and_fashion。
4. steps 只能从 resolve_city、fetch_weather、generate_outfit 中选择。
5. fallback_policy 只能从 alias_lookup、llm_city_resolution、direct_geocoding、q_weather_fallback、rule_based_fashion、demo_weather 中选择。
"""


ALLOWED_STEPS = ["resolve_city", "fetch_weather", "generate_outfit"]
ALLOWED_FALLBACKS = [
    "alias_lookup",
    "llm_city_resolution",
    "direct_geocoding",
    "q_weather_fallback",
    "rule_based_fashion",
    "demo_weather",
]


class MultiAgentCoordinator:
    """基于 LangGraph 状态流的多智能体协调器。"""

    def __init__(self):
        self.weather_service = Weather()
        self.fashion_agent = FashionAgent()
        self.dependency_status = gather_runtime_health()

    def _timestamp(self) -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    def _default_fallback_policy(self) -> list[str]:
        fallbacks = [
            "alias_lookup",
            "llm_city_resolution",
            "direct_geocoding",
            "q_weather_fallback",
            "rule_based_fashion",
        ]
        if not self.dependency_status.get("openweather_configured", False):
            fallbacks.append("demo_weather")
        return fallbacks

    def _default_plan(self, user_input: str, source: str = "default_safety_plan") -> QueryPlan:
        return QueryPlan(
            intent="weather_and_fashion",
            raw_location=extract_probable_location(user_input),
            need_resolution=True,
            need_clarification=False,
            steps=list(ALLOWED_STEPS),
            fallback_policy=self._default_fallback_policy(),
            source=source,
        )

    def _sanitize_plan_list(self, payload_value, allowed_values: list[str], default_values: list[str]) -> list[str]:
        if not isinstance(payload_value, list):
            return list(default_values)
        cleaned = [item for item in payload_value if isinstance(item, str) and item in allowed_values]
        return cleaned or list(default_values)

    def _parse_plan(self, user_input: str, raw_output: str) -> QueryPlan:
        payload = extract_json_payload(raw_output)
        default_plan = self._default_plan(user_input, source="default_safety_plan")
        if not isinstance(payload, dict):
            return default_plan

        return QueryPlan(
            intent=str(payload.get("intent", default_plan.intent)),
            raw_location=str(payload.get("raw_location", default_plan.raw_location)).strip() or default_plan.raw_location,
            need_resolution=bool(payload.get("need_resolution", True)),
            need_clarification=bool(payload.get("need_clarification", False)),
            steps=self._sanitize_plan_list(payload.get("steps"), ALLOWED_STEPS, default_plan.steps),
            fallback_policy=self._sanitize_plan_list(
                payload.get("fallback_policy"),
                ALLOWED_FALLBACKS,
                default_plan.fallback_policy,
            ),
            source="llm_plan",
            raw_text=raw_output,
        )

    def _should_use_planner(self, user_input: str, selected_candidate_id: str = "") -> bool:
        if selected_candidate_id:
            return False
        if not self.dependency_status.get("llm_configured"):
            return False
        return is_complex_weather_query(user_input)

    def _fast_path_plan_record(self, request_id: str, decision_reason: str) -> ExecutionRecord:
        return ExecutionRecord(
            role="规则规划",
            name="FastPathPlanner",
            node_name="planner",
            provider="rule_router",
            request_id=request_id,
            success=True,
            used_llm=False,
            fallback_used=False,
            elapsed_ms=0,
            decision_reason=decision_reason,
            metadata={"used_fast_path": True, "framework": "workflow_router"},
        )

    def plan_query(self, user_input: str, request_id: str) -> tuple[QueryPlan, ExecutionRecord]:
        prompt = (
            "请根据下面的用户输入生成执行计划 JSON。\n"
            f"用户输入: {user_input}\n"
            "只输出 JSON。"
        )
        output, record = run_agent(
            role="协调器规划",
            name="SupervisorPlanner",
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            prompt=prompt,
            json_mode=True,
        )
        record.request_id = request_id
        record.node_name = "planner"
        record.decision_reason = "complex_query_supervisor"
        if record.success and output:
            return self._parse_plan(user_input, output), record
        return self._default_plan(user_input), record

    def _build_resolution_trace(self, request_id: str, resolution_result) -> ExecutionRecord:
        selected = resolution_result.selected.display_name if resolution_result.selected else ""
        return ExecutionRecord(
            role="城市解析服务",
            name="CityResolver",
            node_name="resolve_city",
            provider="hybrid_resolution",
            request_id=request_id,
            success=resolution_result.resolution_status in {"resolved", "needs_clarification"},
            used_llm=resolution_result.used_llm,
            fallback_used=resolution_result.fallback_used,
            output_summary=compact_text(json.dumps(resolution_result.to_dict(), ensure_ascii=False)),
            metadata={
                "resolution_status": resolution_result.resolution_status,
                "selected_city": selected,
                "validated_candidates": len(resolution_result.validated_candidates),
                "clarification_candidates": len(resolution_result.clarification_candidates),
            },
        )

    def _build_weather_trace(self, request_id: str, selected_candidate, weather_result) -> ExecutionRecord:
        return ExecutionRecord(
            role="天气服务",
            name="OpenWeather",
            node_name="fetch_weather",
            provider="openweather",
            request_id=request_id,
            input_summary=compact_text(json.dumps(selected_candidate.to_dict(), ensure_ascii=False)),
            output_summary=compact_text(json.dumps(weather_result.to_dict(), ensure_ascii=False)),
            success=weather_result.ok,
            used_llm=False,
            fallback_used=weather_result.fallback_used,
            elapsed_ms=weather_result.request_elapsed_ms,
            error=weather_result.error,
            metadata={
                "data_mode": weather_result.data_mode,
                "source": weather_result.source,
                "observed_at_local": weather_result.observed_at_local,
                "daily_range_text": weather_result.daily_range_text,
            },
        )

    def _build_clarify_trace(self, request_id: str, result: CoordinatorResult) -> ExecutionRecord:
        return ExecutionRecord(
            role="人工澄清",
            name="ClarifyCity",
            node_name="clarify_city",
            provider="human_in_the_loop",
            request_id=request_id,
            success=True,
            used_llm=False,
            fallback_used=False,
            decision_reason=result.resolution.clarification_message or result.resolution.failure_reason,
            metadata={
                "candidate_count": len(result.resolution.clarification_candidates),
                "message": result.resolution.clarification_message or result.resolution.failure_reason,
            },
        )

    def _run_resolution_step(self, result: CoordinatorResult, preferred_candidate_id: str = "") -> bool:
        resolution = resolve_city(
            result.plan.raw_location or result.user_input,
            self.weather_service,
            fallback_policy=set(result.plan.fallback_policy),
            preferred_candidate_id=preferred_candidate_id,
            fast_mode=result.used_fast_path,
        )
        result.resolution = resolution
        for record in resolution.execution_records:
            record.request_id = result.request_id
            record.node_name = record.node_name or "resolve_city"
        result.execution_trace.extend(resolution.execution_records)
        result.execution_trace.append(self._build_resolution_trace(result.request_id, resolution))

        if resolution.resolution_status == "resolved":
            record_metric("resolution_resolved")
            return True
        if resolution.resolution_status == "needs_clarification":
            record_metric("resolution_needs_clarification")
            result.message = resolution.clarification_message or resolution.failure_reason or "需要先确认城市候选。"
            result.error = resolution.failure_reason or ""
            return False

        record_metric("resolution_failed")
        result.message = resolution.failure_reason or "未能识别出可查询天气的城市。"
        result.error = result.message
        return False

    def _run_weather_step(self, result: CoordinatorResult) -> bool:
        if not result.resolution.selected:
            result.error = result.error or "缺少已选中的城市候选。"
            result.message = result.message or "城市解析未完成，无法查询天气。"
            return False

        allow_q_fallback = "q_weather_fallback" in result.plan.fallback_policy
        weather_result = self.weather_service.get_weather_for_candidate(
            result.resolution.selected,
            allow_q_fallback=allow_q_fallback,
        )
        result.weather = weather_result
        result.execution_trace.append(
            self._build_weather_trace(result.request_id, result.resolution.selected, weather_result)
        )
        record_metric(f"weather_mode_{weather_result.data_mode}")

        if weather_result.ok:
            return True

        if (
            "demo_weather" in result.plan.fallback_policy
            and result.resolution.selected is not None
            and self.weather_service.demo_mode
        ):
            demo_result = self.weather_service._build_demo_weather(result.resolution.selected)
            demo_result.request_elapsed_ms = weather_result.request_elapsed_ms
            result.weather = demo_result
            result.execution_trace.append(
                self._build_weather_trace(result.request_id, result.resolution.selected, demo_result)
            )
            record_metric("weather_mode_demo")
            return True

        result.error = weather_result.error or "天气查询失败。"
        result.message = "天气查询未成功。"
        return False

    def _run_fashion_step(self, result: CoordinatorResult) -> bool:
        if not result.weather.ok:
            result.error = result.error or "缺少有效天气结果，无法生成穿搭建议。"
            result.message = result.message or "天气结果不可用，无法生成穿搭建议。"
            return False

        fashion_result = self.fashion_agent.get_fashion_advice(result.weather)
        for record in fashion_result.execution_records:
            record.request_id = result.request_id
            record.node_name = record.node_name or "generate_outfit"
        result.fashion = fashion_result
        result.execution_trace.extend(fashion_result.execution_records)
        record_metric("fashion_llm_success" if fashion_result.used_llm else "fashion_rule_fallback")
        return bool(fashion_result.advice_text)

    def _finalize_warnings(self, result: CoordinatorResult, plan_record: ExecutionRecord):
        warnings: list[str] = []
        modules = self.dependency_status.get("modules", {})

        if not modules.get("langchain", {}).get("available", False) or not modules.get(
            "langchain_openai", {}
        ).get("available", False):
            warnings.append("未安装完整的 LangChain 运行栈，LLM 节点会自动走兜底逻辑。")
        if not modules.get("langgraph", {}).get("available", False):
            warnings.append("未安装 LangGraph，当前使用兼容工作流执行器；安装后会自动切换到 LangGraph。")
        if not self.dependency_status["llm_configured"]:
            missing = ", ".join(self.dependency_status["missing_llm_fields"])
            warnings.append(f"LLM 配置不完整: {missing}")
        if not self.dependency_status["openweather_configured"]:
            warnings.append("未配置 OPENWEATHER_API_KEY，天气数据将只能使用 demo 模式。")

        for module_name in ["gradio", "fastapi", "pydantic", "typing_extensions"]:
            info = modules.get(module_name, {})
            if info and not info.get("available", True):
                warnings.append(f"{module_name} 依赖异常: {info.get('error')}")

        if plan_record.error:
            warnings.append(f"Supervisor 规划提示: {plan_record.error}")
        for record in result.execution_trace:
            if record.error:
                warnings.append(f"{record.name} 提示: {record.error}")
        if result.weather.ok and result.weather.data_mode == "demo":
            warnings.append("当前天气结果来自 demo 演示数据，不是真实在线天气。")
        if not result.weather.ok and result.weather.error:
            warnings.append(f"天气服务提示: {result.weather.error}")
        if result.fashion.error:
            warnings.append(f"穿衣建议提示: {result.fashion.error}")
        if result.used_fast_path:
            warnings.append("本次查询使用了快速路径：普通地点输入会优先跳过 Supervisor LLM。")

        result.warnings = list(dict.fromkeys(warnings))

    def _step_enabled(self, result: CoordinatorResult, step_name: str) -> bool:
        steps = result.plan.steps or list(ALLOWED_STEPS)
        return step_name in steps

    def graph_planner_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        selected_candidate_id = state.get("selected_candidate_id", "")
        decision_reason = "simple_query_fast_path"

        if self._should_use_planner(result.user_input, selected_candidate_id=selected_candidate_id):
            plan, plan_record = self.plan_query(result.user_input, result.request_id)
            result.used_fast_path = False
            record_metric("planner_llm_used")
            decision_reason = "complex_query_supervisor"
        else:
            plan = self._default_plan(
                result.user_input,
                source="clarification_follow_up" if selected_candidate_id else "fast_path_plan",
            )
            plan_record = self._fast_path_plan_record(result.request_id, decision_reason=decision_reason)
            result.used_fast_path = True
            record_metric("planner_fast_path")

        result.plan = plan
        result.execution_trace.append(plan_record)
        state["plan_record"] = plan_record
        state["decision_reason"] = decision_reason
        return state

    def graph_resolve_city_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        if not self._step_enabled(result, "resolve_city") and not result.plan.need_resolution:
            state["resolution_step_ok"] = True
            return state

        state["resolution_step_ok"] = self._run_resolution_step(
            result,
            preferred_candidate_id=state.get("selected_candidate_id", ""),
        )
        return state

    def graph_fetch_weather_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        state["weather_step_ok"] = self._run_weather_step(result)
        return state

    def graph_generate_outfit_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        state["fashion_step_ok"] = self._run_fashion_step(result)
        return state

    def graph_clarify_city_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        result.execution_trace.append(self._build_clarify_trace(result.request_id, result))
        return state

    def graph_finalize_node(self, state: QueryState) -> QueryState:
        result = state["result"]
        plan_record = state.get("plan_record") or ExecutionRecord(role="planner", name="planner")
        self._finalize_warnings(result, plan_record)

        resolution_required = self._step_enabled(result, "resolve_city") or result.plan.need_resolution
        weather_required = self._step_enabled(result, "fetch_weather")
        fashion_required = self._step_enabled(result, "generate_outfit")

        resolution_ok = (not resolution_required) or result.resolution.resolution_status == "resolved"
        weather_ok = (not weather_required) or result.weather.ok
        fashion_ok = (not fashion_required) or bool(result.fashion.advice_text)
        result.ok = bool(resolution_ok and weather_ok and fashion_ok and not result.resolution.need_clarification)

        if result.resolution.need_clarification and not state.get("selected_candidate_id"):
            result.message = result.message or "需要先确认城市候选。"
        elif result.ok:
            if weather_required and not fashion_required:
                result.message = "天气查询完成"
            else:
                result.message = "查询完成"
        elif not result.message:
            result.message = "查询未完全成功"

        result.graph_runtime = state.get("graph_runtime", "compat_state_graph")
        result.total_elapsed_ms = int((time.time() - state["started_at"]) * 1000)
        result.completed_at = self._timestamp()
        result.metrics_snapshot = metrics_snapshot()

        log_event(
            "query_completed",
            request_id=result.request_id,
            ok=result.ok,
            resolution_status=result.resolution.resolution_status,
            weather_mode=result.weather.data_mode,
            fashion_source=result.fashion.source,
            used_fast_path=result.used_fast_path,
            graph_runtime=result.graph_runtime,
            total_elapsed_ms=result.total_elapsed_ms,
        )
        return state

    def route_after_resolve_city(self, state: QueryState) -> str:
        result = state["result"]
        if result.resolution.need_clarification and not state.get("selected_candidate_id"):
            return "clarify_city"
        if not state.get("resolution_step_ok", False):
            return "finalize"
        if not self._step_enabled(result, "fetch_weather"):
            return "finalize"
        return "fetch_weather"

    def route_after_fetch_weather(self, state: QueryState) -> str:
        result = state["result"]
        if not state.get("weather_step_ok", False):
            return "finalize"
        if not self._step_enabled(result, "generate_outfit"):
            return "finalize"
        return "generate_outfit"

    def process_query(self, user_input: str, selected_candidate_id: str = "") -> CoordinatorResult:
        request_id = new_request_id()
        record_metric("requests_total")
        log_event(
            "query_started",
            request_id=request_id,
            user_input=user_input,
            selected_candidate_id=selected_candidate_id,
        )

        result = CoordinatorResult(
            ok=False,
            request_id=request_id,
            user_input=user_input,
            dependency_status=self.dependency_status,
            requested_at=self._timestamp(),
        )
        state: QueryState = {
            "request_id": request_id,
            "selected_candidate_id": selected_candidate_id,
            "result": result,
            "started_at": time.time(),
        }
        final_state = run_query_workflow(self, state)
        return final_state["result"]

    def get_weather_only(self, city_name: str):
        resolution = resolve_city(
            city_name,
            self.weather_service,
            fallback_policy=set(self._default_fallback_policy()),
            fast_mode=not self._should_use_planner(city_name),
        )
        if resolution.selected is None:
            return resolution.to_dict()
        return self.weather_service.get_weather_for_candidate(resolution.selected).to_dict()

    def get_fashion_advice_only(self, weather_info):
        if isinstance(weather_info, dict):
            weather_result = WeatherResult(**weather_info)
        else:
            weather_result = self.weather_service.get_weather_by_query(str(weather_info))
        return self.fashion_agent.get_fashion_advice(weather_result).to_dict()


def main():
    coordinator = MultiAgentCoordinator()
    result = coordinator.process_query("帮我查今天东京天气并给穿搭")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
