"""
Gradio 前端界面。
默认自动选择可用端口，也可以通过环境变量 GRADIO_SERVER_PORT 指定端口。
"""
from __future__ import annotations

import os
import sys
from typing import Any

from health_check import format_health_report, gather_runtime_health
from multi_agent_coordinator import MultiAgentCoordinator
from presentation import build_result_view_model

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

MAX_HISTORY = 8


def console_print(text: str):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = str(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe_text)


def _push_history(history: list[str] | None, query: str) -> list[str]:
    history = list(history or [])
    query = (query or "").strip()
    if not query:
        return history
    history = [item for item in history if item != query]
    history.insert(0, query)
    return history[:MAX_HISTORY]


def _empty_view_model(history: list[str] | None = None, message: str = "请输入城市名称") -> dict[str, Any]:
    return {
        "summary": {
            "request_id": "",
            "user_input": "",
            "plan_intent": "",
            "plan_location": "",
            "selected_city": "",
            "resolution_status": "failed",
            "resolution_confidence": 0.0,
            "message": message,
            "error": message,
            "used_fast_path": False,
            "graph_runtime": "",
            "total_elapsed_ms": 0,
            "requested_at": "",
            "completed_at": "",
            "models_used": [],
        },
        "weather": {
            "ok": False,
            "city": "",
            "coords": "",
            "temperature": "",
            "feels_like": "",
            "temp_min": "",
            "temp_max": "",
            "daily_range_text": "",
            "description": "",
            "humidity": "",
            "wind": "",
            "source": "",
            "data_mode": "error",
            "observed_at": "",
            "observed_at_local": "",
            "city_local_time": "",
            "request_elapsed_ms": 0,
            "error": message,
        },
        "fashion": {
            "text": "",
            "time_of_day_advice": "",
            "layering_advice": "",
            "source": "",
            "used_llm": False,
            "error": "",
        },
        "clarification": {
            "needed": False,
            "message": "",
            "recommended_candidate_id": "",
            "recommended_label": "",
            "options": [],
        },
        "trace": [],
        "warnings": [message] if message else [],
        "dependency_status": gather_runtime_health(),
        "badges": [],
        "recent_queries": history or [],
        "metrics_snapshot": {},
    }


def _badge_html(view_model: dict[str, Any]) -> str:
    chips = []
    for label, value in view_model.get("badges", []):
        text_value = str(value)
        color = "#1f7a8c"
        if text_value in {"否", "error"}:
            color = "#b23a48"
        if text_value in {"demo", "real_q_fallback"}:
            color = "#a16207"
        if label in {"总耗时", "工作流运行时"}:
            color = "#2563eb"
        chips.append(
            "<span style='display:inline-block;margin:4px 8px 4px 0;padding:6px 10px;"
            f"border-radius:999px;background:{color};color:white;font-size:12px;'>{label}: {text_value}</span>"
        )
    return "".join(chips) or "<span>暂无状态标签</span>"


def _clarification_cards_html(view_model: dict[str, Any]) -> str:
    clarification = view_model.get("clarification", {})
    options = clarification.get("options", [])
    if not options:
        return "<div style='color:#666;'>当前没有需要人工确认的候选城市。</div>"

    cards = []
    for item in options:
        badge = ""
        if item.get("recommended"):
            badge = (
                "<span style='display:inline-block;padding:3px 8px;border-radius:999px;"
                "background:#14532d;color:#fff;font-size:12px;margin-bottom:8px;'>推荐候选</span>"
            )
        coords = f"<div style='font-size:12px;color:#666;'>坐标: {item['coords']}</div>" if item.get("coords") else ""
        cards.append(
            "<div style='border:1px solid #d5d8dc;border-radius:14px;padding:12px;margin:10px 0;background:#fff;'>"
            f"{badge}"
            f"<div style='font-size:16px;font-weight:700;color:#1f2937;'>{item['label']}</div>"
            f"<div style='font-size:13px;color:#4b5563;margin-top:6px;'>置信度 {item['confidence']:.2f} | 来源: {item['source']}</div>"
            f"{coords}"
            f"<div style='font-size:13px;color:#374151;margin-top:8px;'>{item['reason']}</div>"
            "</div>"
        )
    return "".join(cards)


def _trace_markdown(view_model: dict[str, Any]) -> str:
    lines = []
    for record in view_model.get("trace", []):
        status = "成功" if record.get("success") else "未成功"
        lines.append(
            f"- {record.get('node_name') or record.get('role', '')}/{record.get('name', '')}: "
            f"状态={status}，provider={record.get('provider') or '无'}，"
            f"model={record.get('model') or '未使用'}，"
            f"调用LLM={'是' if record.get('used_llm') else '否'}，"
            f"兜底={'是' if record.get('fallback_used') else '否'}，"
            f"耗时={record.get('elapsed_ms', 0)}ms"
        )
        if record.get("decision_reason"):
            lines.append(f"  决策原因: {record['decision_reason']}")
        metadata = record.get("metadata") or {}
        if metadata:
            lines.append(f"  元数据: {metadata}")
        if record.get("error"):
            lines.append(f"  错误: {record['error']}")
    return "\n".join(lines) if lines else "- 暂无执行记录"


def _health_markdown(view_model: dict[str, Any]) -> str:
    dependency_status = view_model["dependency_status"]
    web_stack = dependency_status.get("web_stack", {})
    lines = [
        f"- Python: {dependency_status.get('python_version', 'unknown')}",
        f"- LLM 配置完整: {'是' if dependency_status.get('llm_configured') else '否'}",
        f"- OpenWeather 已配置: {'是' if dependency_status.get('openweather_configured') else '否'}",
        f"- Web 栈兼容: {'是' if web_stack.get('compatible') else '否'}",
    ]
    modules = dependency_status.get("modules", {})
    for name in [
        "gradio",
        "fastapi",
        "pydantic",
        "typing_extensions",
        "huggingface_hub",
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langgraph",
        "fastmcp",
    ]:
        info = modules.get(name, {})
        status = "OK" if info.get("available") else "ERROR"
        suffix = f" ({info.get('version')})" if info.get("version") else ""
        line = f"- {name}: {status}{suffix}"
        if info.get("error"):
            line += f" -> {info['error']}"
        lines.append(line)

    issues = web_stack.get("issues", [])
    if issues:
        lines.append("")
        lines.append("兼容性提示:")
        lines.extend(f"- {item}" for item in issues)
    return "\n".join(lines)


def _render_text_sections(view_model: dict[str, Any]) -> dict[str, str]:
    summary = view_model["summary"]
    weather = view_model["weather"]
    fashion = view_model["fashion"]
    clarification = view_model["clarification"]
    metrics = view_model.get("metrics_snapshot", {})
    models_used = summary.get("models_used", [])

    summary_md = f"""
### 用户输入与识别结果
- 请求 ID: `{summary["request_id"]}`
- 原始输入: {summary["user_input"] or "无"}
- 规划意图: {summary["plan_intent"] or "无"}
- 规划提取地点: {summary["plan_location"] or "无"}
- 最终识别: {summary["selected_city"] or "无"}
- 解析状态: {summary["resolution_status"]}
- 解析置信度: {summary["resolution_confidence"]:.2f}
- 查询时间: {summary["requested_at"] or "无"}
- 完成时间: {summary["completed_at"] or "无"}
- 总耗时: {summary["total_elapsed_ms"]}ms
- 查询路径: {"快速路径" if summary["used_fast_path"] else "Supervisor 规划"}
- 工作流运行时: {summary["graph_runtime"] or "未知"}
- 使用模型: {", ".join(models_used) if models_used else "未调用 LLM"}
- 系统消息: {summary["message"] or "无"}
"""

    weather_md = f"""
### 天气信息
- 查询状态: {"成功" if weather["ok"] else "失败"}
- 城市: {weather["city"] or "无"}
- 坐标: {weather["coords"] or "无"}
- 当前温度: {weather["temperature"] or "无"}
- 体感温度: {weather["feels_like"] or "无"}
- 今日最低温: {weather["temp_min"] or "无"}
- 今日最高温: {weather["temp_max"] or "无"}
- 今日温度范围: {weather["daily_range_text"] or "无"}
- 天气: {weather["description"] or "无"}
- 湿度: {weather["humidity"] or "无"}
- 风速: {weather["wind"] or "无"}
- 天气数据时间: {weather["observed_at_local"] or weather["observed_at"] or "无"}
- 目标城市当地时间: {weather["city_local_time"] or "无"}
- 天气服务耗时: {weather["request_elapsed_ms"]}ms
- 数据模式: {weather["data_mode"]}
- 数据来源: {weather["source"] or "无"}
"""
    if weather["error"]:
        weather_md += f"\n- 错误: {weather['error']}\n"

    fashion_md = f"""
### 穿衣建议
{fashion["text"] or "暂无穿衣建议"}

来源: {fashion["source"] or "无"} | 使用 LLM: {"是" if fashion["used_llm"] else "否"}
"""
    if fashion["error"]:
        fashion_md += f"\n错误: {fashion['error']}\n"

    clarification_md = ""
    if clarification["needed"]:
        clarification_md = "### 需要澄清\n"
        clarification_md += f"- 原因: {clarification['message'] or '请确认你想查询的候选城市'}\n"
        if clarification.get("recommended_label"):
            clarification_md += f"- 推荐候选: {clarification['recommended_label']}\n"
        clarification_md += "\n".join(
            f"- {item['label']}（置信度 {item['confidence']:.2f}，来源 {item['source']}）"
            for item in clarification["options"]
        ) or "- 暂无候选"

    warnings = view_model.get("warnings", [])
    warnings_md = "### 提示与警告\n" + ("\n".join(f"- {item}" for item in warnings) if warnings else "- 无")

    metrics_md = ""
    if metrics:
        metrics_md = "\n".join(f"- {key}: {value}" for key, value in sorted(metrics.items()))

    trace_md = "### 执行链路\n" + _trace_markdown(view_model)
    if metrics_md:
        trace_md += "\n\n### 进程累计指标\n" + metrics_md

    health_md = "### 环境与依赖状态\n" + _health_markdown(view_model)
    return {
        "summary_md": summary_md.strip(),
        "weather_md": weather_md.strip(),
        "fashion_md": fashion_md.strip(),
        "trace_md": trace_md.strip(),
        "warnings_md": warnings_md.strip(),
        "health_md": health_md.strip(),
        "clarification_md": clarification_md.strip(),
        "badge_html": _badge_html(view_model),
    }


def _build_output_payload(view_model: dict[str, Any], history: list[str], gr) -> tuple[Any, ...]:
    sections = _render_text_sections(view_model)
    candidate_choices = [
        (
            f"{'★' if item['recommended'] else ''}{item['label']} | 置信度 {item['confidence']:.2f} | {item['source']}",
            item["candidate_id"],
        )
        for item in view_model["clarification"]["options"]
    ]
    recommended_candidate_id = view_model["clarification"].get("recommended_candidate_id", "")
    show_candidates = bool(candidate_choices)
    return (
        sections["summary_md"],
        sections["weather_md"],
        sections["fashion_md"],
        sections["trace_md"],
        sections["warnings_md"],
        sections["health_md"],
        sections["clarification_md"],
        sections["badge_html"],
        _clarification_cards_html(view_model),
        gr.update(choices=candidate_choices, value=(recommended_candidate_id or None), visible=show_candidates),
        gr.update(visible=show_candidates),
        gr.update(visible=show_candidates and bool(recommended_candidate_id)),
        history,
        gr.update(choices=history, value=(history[0] if history else None)),
        {
            "user_input": view_model["summary"].get("user_input", ""),
            "clarification_options": view_model["clarification"]["options"],
            "recommended_candidate_id": recommended_candidate_id,
        },
    )


def _build_clear_payload(gr) -> tuple[Any, ...]:
    empty_view_model = _empty_view_model([], "")
    payload = _build_output_payload(empty_view_model, [], gr)
    return ("",) + payload


def get_weather_and_fashion_advice(city_name: str) -> str:
    city_name = (city_name or "").strip()
    if not city_name:
        return "请输入城市名称。"
    coordinator = MultiAgentCoordinator()
    result = coordinator.process_query(city_name)
    view_model = build_result_view_model(result)
    sections = _render_text_sections(view_model)
    return "\n\n".join(
        section
        for section in [
            sections["summary_md"],
            sections["weather_md"],
            sections["fashion_md"],
            sections["trace_md"],
            sections["warnings_md"],
            sections["health_md"],
            sections["clarification_md"],
        ]
        if section
    )


def create_gradio_interface():
    try:
        import gradio as gr
    except Exception as exc:
        raise RuntimeError(
            "Gradio 导入失败，请先执行 `python health_check.py` 检查环境，再按 requirements-web.txt 修复 Web 依赖。"
        ) from exc

    description = """
# FashionDailyDress Agent Team Demo

这个页面会把结果拆开展示：
- 识别结果
- 天气数据
- 穿衣建议
- 执行链路
- 环境状态
- 歧义城市候选选择
"""

    coordinator = MultiAgentCoordinator()

    def run_query(city_name, history):
        city_name = (city_name or "").strip()
        if not city_name:
            return _build_output_payload(_empty_view_model(history), history or [], gr)

        result = coordinator.process_query(city_name)
        history = _push_history(history, city_name)
        view_model = build_result_view_model(result, history)
        return _build_output_payload(view_model, history, gr)

    def confirm_candidate(query_state, selected_candidate_id, history):
        user_input = (query_state or {}).get("user_input", "")
        if not user_input or not selected_candidate_id:
            return run_query(user_input, history)

        result = coordinator.process_query(user_input, selected_candidate_id=selected_candidate_id)
        history = _push_history(history, user_input)
        view_model = build_result_view_model(result, history)
        return _build_output_payload(view_model, history, gr)

    def use_recommended_candidate(query_state, history):
        recommended_candidate_id = (query_state or {}).get("recommended_candidate_id", "")
        return confirm_candidate(query_state, recommended_candidate_id, history)

    def rerun_recent(selected_recent, history):
        return run_query(selected_recent, history)

    health_report = format_health_report(gather_runtime_health())

    with gr.Blocks(
        title="FashionDailyDress Agent Team Demo",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { max-width: 1180px !important; }
        .panel { border: 1px solid #d9d9d9; border-radius: 12px; padding: 12px; background: #ffffff; }
        """,
    ) as demo:
        history_state = gr.State([])
        query_state = gr.State({})

        gr.Markdown(description)
        gr.Markdown("### 启动环境体检（非本次请求）")
        gr.Textbox(value=health_report, lines=16, show_copy_button=True, interactive=False)

        with gr.Row():
            with gr.Column(scale=1):
                city_input = gr.Textbox(
                    label="请输入城市名称",
                    placeholder="例如：北京、Beijing、伦敦 London、springfield",
                    info="支持中文、英文和中英混合地点输入",
                )
                submit_btn = gr.Button("查询天气和穿搭", variant="primary", size="lg")
                clear_btn = gr.Button("清空", variant="secondary")
                recent_dropdown = gr.Dropdown(
                    label="最近查询",
                    choices=[],
                    value=None,
                    interactive=True,
                    allow_custom_value=False,
                )
                recent_btn = gr.Button("重试最近查询", variant="secondary")
                candidate_cards_html = gr.HTML(visible=True)
                candidate_radio = gr.Radio(label="请选择候选城市", choices=[], visible=False)
                confirm_btn = gr.Button("使用所选候选继续", visible=False)
                use_recommended_btn = gr.Button("一键使用推荐候选", visible=False, variant="primary")

            with gr.Column(scale=2):
                badge_html = gr.HTML()
                with gr.Row():
                    with gr.Column(elem_classes="panel"):
                        summary_md = gr.Markdown()
                    with gr.Column(elem_classes="panel"):
                        weather_md = gr.Markdown()
                with gr.Row():
                    with gr.Column(elem_classes="panel"):
                        fashion_md = gr.Markdown()
                    with gr.Column(elem_classes="panel"):
                        clarification_md = gr.Markdown()
                with gr.Row():
                    with gr.Column(elem_classes="panel"):
                        trace_md = gr.Markdown()
                    with gr.Column(elem_classes="panel"):
                        warnings_md = gr.Markdown()
                health_md = gr.Markdown()

        examples = [["北京"], ["shanghai"], ["东京涩谷"], ["伦敦 London"], ["springfield"], ["帮我查今天东京天气并给穿搭"]]
        gr.Examples(examples=examples, inputs=city_input, label="快速体验")

        outputs = [
            summary_md,
            weather_md,
            fashion_md,
            trace_md,
            warnings_md,
            health_md,
            clarification_md,
            badge_html,
            candidate_cards_html,
            candidate_radio,
            confirm_btn,
            use_recommended_btn,
            history_state,
            recent_dropdown,
            query_state,
        ]

        submit_btn.click(fn=run_query, inputs=[city_input, history_state], outputs=outputs)
        city_input.submit(fn=run_query, inputs=[city_input, history_state], outputs=outputs)
        recent_btn.click(fn=rerun_recent, inputs=[recent_dropdown, history_state], outputs=outputs)
        confirm_btn.click(fn=confirm_candidate, inputs=[query_state, candidate_radio, history_state], outputs=outputs)
        use_recommended_btn.click(fn=use_recommended_candidate, inputs=[query_state, history_state], outputs=outputs)
        clear_btn.click(fn=lambda: _build_clear_payload(gr), inputs=[], outputs=[city_input] + outputs)

    return demo


def get_launch_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "server_name": "0.0.0.0",
        "share": False,
        "show_error": True,
        "debug": True,
        "quiet": False,
        "inbrowser": False,
    }

    port_str = os.getenv("GRADIO_SERVER_PORT", "").strip()
    if not port_str:
        return kwargs

    try:
        port = int(port_str)
    except ValueError:
        console_print(f"环境变量 GRADIO_SERVER_PORT={port_str} 不是合法整数，已改为自动选端口。")
        return kwargs

    if 1 <= port <= 65535:
        kwargs["server_port"] = port
    else:
        console_print(f"环境变量 GRADIO_SERVER_PORT={port_str} 不在有效范围内，已改为自动选端口。")
    return kwargs


def main():
    console_print("启动 FashionDailyDress Agent Team Demo - Gradio 前端")
    port_str = os.getenv("GRADIO_SERVER_PORT", "").strip()
    if port_str:
        console_print(f"检测到固定端口配置: GRADIO_SERVER_PORT={port_str}")
    else:
        console_print("未设置固定端口，Gradio 将自动选择空闲端口。")

    try:
        demo = create_gradio_interface()
    except RuntimeError as exc:
        console_print(str(exc))
        return

    try:
        demo.launch(**get_launch_kwargs())
    except Exception as exc:
        console_print("Gradio 启动失败，请先执行 `python health_check.py` 查看依赖状态。")
        console_print(str(exc))


if __name__ == "__main__":
    main()
