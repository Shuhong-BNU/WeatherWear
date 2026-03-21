from __future__ import annotations

from typing import Callable

from app_types import QueryState
from llm_support import is_module_available


def _planner_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_planner_node(state)


def _resolve_city_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_resolve_city_node(state)


def _fetch_weather_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_fetch_weather_node(state)


def _generate_outfit_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_generate_outfit_node(state)


def _clarify_city_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_clarify_city_node(state)


def _finalize_node(coordinator, state: QueryState) -> QueryState:
    return coordinator.graph_finalize_node(state)


def _build_langgraph_runner(coordinator) -> Callable[[QueryState], QueryState] | None:
    if not is_module_available("langgraph"):
        return None

    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(dict)
    graph.add_node("planner", lambda state: _planner_node(coordinator, state))
    graph.add_node("resolve_city", lambda state: _resolve_city_node(coordinator, state))
    graph.add_node("fetch_weather", lambda state: _fetch_weather_node(coordinator, state))
    graph.add_node("generate_outfit", lambda state: _generate_outfit_node(coordinator, state))
    graph.add_node("clarify_city", lambda state: _clarify_city_node(coordinator, state))
    graph.add_node("finalize", lambda state: _finalize_node(coordinator, state))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "resolve_city")
    graph.add_conditional_edges(
        "resolve_city",
        coordinator.route_after_resolve_city,
        {
            "fetch_weather": "fetch_weather",
            "clarify_city": "clarify_city",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "fetch_weather",
        coordinator.route_after_fetch_weather,
        {
            "generate_outfit": "generate_outfit",
            "finalize": "finalize",
        },
    )
    graph.add_edge("generate_outfit", "finalize")
    graph.add_edge("clarify_city", "finalize")
    graph.add_edge("finalize", END)

    compiled = graph.compile()
    return lambda state: compiled.invoke(state)


def _run_compat_workflow(coordinator, state: QueryState) -> QueryState:
    state = _planner_node(coordinator, state)
    state = _resolve_city_node(coordinator, state)
    next_step = coordinator.route_after_resolve_city(state)
    if next_step == "fetch_weather":
        state = _fetch_weather_node(coordinator, state)
        next_step = coordinator.route_after_fetch_weather(state)
        if next_step == "generate_outfit":
            state = _generate_outfit_node(coordinator, state)
    elif next_step == "clarify_city":
        state = _clarify_city_node(coordinator, state)
    state = _finalize_node(coordinator, state)
    return state


def run_query_workflow(coordinator, state: QueryState) -> QueryState:
    runner = _build_langgraph_runner(coordinator)
    if runner is None:
        state["graph_runtime"] = "compat_state_graph"
        return _run_compat_workflow(coordinator, state)
    state["graph_runtime"] = "langgraph"
    return runner(state)
