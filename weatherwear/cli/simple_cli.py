from __future__ import annotations

from weatherwear.support.health_check import format_health_report, gather_runtime_health
from weatherwear.application.coordinator import MultiAgentCoordinator
from weatherwear.application.presentation import build_result_view_model
from weatherwear.support.common_utils import safe_console_print


def render_cli_report(view_model: dict) -> str:
    hero = view_model["hero_summary"]
    summary = view_model["summary"]
    weather = view_model["weather"]
    clarification = view_model["clarification"]

    lines = [
        "=" * 64,
        "WeatherWear CLI",
        "=" * 64,
        f"地点: {hero['title']}",
        f"天气: {hero['condition_emoji']} {hero['condition']}",
        f"当前温度: {hero['temperature'] or '无'}",
        f"体感温度: {hero['feels_like'] or '无'}",
        f"今日温度范围: {hero['daily_range_text'] or '无'}",
        f"今日建议: {hero['one_line_advice']}",
        f"查询路径: {hero['query_path'] or '未知'}",
        f"确认模式: {'严格确认' if summary['confirmation_mode'] == 'strict' else '智能模式'}",
        f"地点来源: {summary['location_source_label']}",
        f"工作流: {summary['graph_runtime'] or '未知'}",
        f"总耗时: {summary['total_elapsed_ms']}ms",
        "",
        "天气详情",
        "-" * 64,
        f"坐标: {weather['coords'] or '无'}",
        f"湿度: {weather['humidity'] or '无'}",
        f"风速: {weather['wind'] or '无'}",
        f"天气更新时间: {weather['observed_at_local'] or '无'}",
        f"时区 / 当地时间: {weather['timezone_label'] or '未知'} / {weather['city_local_time'] or '无'}",
        f"数据来源: {weather['source'] or '无'}",
        "",
        "穿搭建议",
        "-" * 64,
    ]
    for section in view_model["fashion_sections"]:
        lines.append(f"[{section['title']}]")
        lines.append(section["content"])
        lines.append("")

    if clarification["needed"]:
        lines.extend(
            [
                "候选确认",
                "-" * 64,
                clarification["message"] or "请选择更准确的候选地点。",
            ]
        )
        lines.extend(
            f"- {item['label']}（candidate_id={item['candidate_id']}，置信度={item['confidence']:.2f}，来源={item['source']}）"
            for item in clarification["options"]
        )

    lines.extend(["", "执行链路", "-" * 64])
    for step in view_model["timeline_steps"]:
        lines.append(
            f"- {step['title']}: status={step['status']}, provider={step['provider'] or '无'}, "
            f"model={step['model'] or '无'}, llm={step['used_llm']}, fallback={step['fallback_used']}, "
            f"elapsed={step['elapsed_ms']}ms"
        )
    return "\n".join(lines)


def get_city_input() -> str | None:
    safe_console_print("欢迎使用 WeatherWear CLI。")
    safe_console_print("支持中文、英文和中英混合地点输入。")
    safe_console_print("输入 'quit' 或 '退出' 可以退出程序。")
    safe_console_print("如遇歧义城市，CLI 会列出 candidate_id，可复制后继续。\n")
    while True:
        city = input("请输入城市名称: ").strip()
        if not city:
            safe_console_print("请输入有效的城市名称。")
            continue
        if city.lower() in {"quit", "exit", "退出"}:
            return None
        return city


def main():
    safe_console_print(format_health_report(gather_runtime_health()))
    safe_console_print("")
    coordinator = MultiAgentCoordinator()

    while True:
        city = get_city_input()
        if city is None:
            safe_console_print("已退出 WeatherWear CLI。")
            return

        confirmation_mode = input("确认模式（smart/strict，默认 smart）: ").strip().lower() or "smart"
        if confirmation_mode not in {"smart", "strict"}:
            confirmation_mode = "smart"

        result = coordinator.process_query(city, confirmation_mode=confirmation_mode)
        view_model = build_result_view_model(result)
        safe_console_print(render_cli_report(view_model))

        if result.resolution.need_clarification and result.resolution.clarification_candidates:
            candidate_id = input("\n如需继续，请输入候选 candidate_id；直接回车则跳过: ").strip()
            if candidate_id:
                follow_up = coordinator.process_query(
                    city,
                    selected_candidate_id=candidate_id,
                    confirmation_mode=confirmation_mode,
                )
                follow_up_view = build_result_view_model(follow_up)
                safe_console_print("\n" + render_cli_report(follow_up_view))


if __name__ == "__main__":
    main()
