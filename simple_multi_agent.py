from __future__ import annotations

import sys

from health_check import format_health_report, gather_runtime_health
from multi_agent_coordinator import MultiAgentCoordinator
from presentation import build_result_view_model


def console_print(text: str):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = str(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe_text)


def render_cli_report(view_model: dict) -> str:
    summary = view_model["summary"]
    weather = view_model["weather"]
    fashion = view_model["fashion"]
    clarification = view_model["clarification"]

    sections = [
        "=" * 60,
        "识别结果",
        "=" * 60,
        f"请求 ID: {summary['request_id']}",
        f"原始输入: {summary['user_input']}",
        f"规划地点: {summary['plan_location']}",
        f"最终识别: {summary['selected_city']}",
        f"解析状态: {summary['resolution_status']}",
        f"解析置信度: {summary['resolution_confidence']:.2f}",
        f"查询路径: {'快速路径' if summary['used_fast_path'] else 'Supervisor 规划'}",
        f"工作流运行时: {summary['graph_runtime'] or '未知'}",
        f"使用模型: {', '.join(summary['models_used']) if summary['models_used'] else '未调用 LLM'}",
        f"总耗时: {summary['total_elapsed_ms']}ms",
        "",
        "=" * 60,
        "天气信息",
        "=" * 60,
        f"状态: {'成功' if weather['ok'] else '失败'}",
        f"城市: {weather['city'] or '无'}",
        f"坐标: {weather['coords'] or '无'}",
        f"当前温度: {weather['temperature'] or '无'}",
        f"体感温度: {weather['feels_like'] or '无'}",
        f"今日最低温: {weather['temp_min'] or '无'}",
        f"今日最高温: {weather['temp_max'] or '无'}",
        f"今日温度范围: {weather['daily_range_text'] or '无'}",
        f"天气: {weather['description'] or '无'}",
        f"湿度: {weather['humidity'] or '无'}",
        f"风速: {weather['wind'] or '无'}",
        f"天气数据时间: {weather['observed_at_local'] or weather['observed_at'] or '无'}",
        f"城市当地时间: {weather['city_local_time'] or '无'}",
        f"天气模式: {weather['data_mode']}",
        f"数据来源: {weather['source'] or '无'}",
    ]
    if weather["error"]:
        sections.append(f"天气错误: {weather['error']}")

    sections.extend(
        [
            "",
            "=" * 60,
            "穿衣建议",
            "=" * 60,
            fashion["text"] or "暂无穿衣建议",
            f"\n来源: {fashion['source'] or '无'} | 使用 LLM: {'是' if fashion['used_llm'] else '否'}",
            "",
            "=" * 60,
            "执行链路",
            "=" * 60,
        ]
    )
    for record in view_model["trace"]:
        sections.append(
            f"- {record.get('node_name') or record['role']}/{record['name']}: "
            f"provider={record.get('provider') or '无'}, "
            f"model={record.get('model') or '无'}, "
            f"used_llm={record['used_llm']}, fallback={record['fallback_used']}, "
            f"elapsed={record.get('elapsed_ms', 0)}ms, error={record['error'] or '无'}"
        )

    if clarification["needed"]:
        sections.extend(
            [
                "",
                "=" * 60,
                "需要澄清",
                "=" * 60,
                clarification["message"] or "请选择更准确的城市候选。",
            ]
        )
        sections.extend(
            f"- {item['label']}（candidate_id={item['candidate_id']}，置信度={item['confidence']:.2f}，来源={item['source']}）"
            for item in clarification["options"]
        )

    sections.extend(["", "=" * 60, "提示", "=" * 60])
    sections.extend(view_model["warnings"] or ["无"])
    return "\n".join(sections)


def get_city_input():
    console_print("欢迎使用 FashionDailyDress Agent Team Demo。")
    console_print("支持中文、英文和中英混合城市名。")
    console_print("输入 'quit' 或 '退出' 可以退出程序。")
    console_print("如遇歧义城市，CLI 会列出 candidate_id，可复制后继续。\n")

    while True:
        city = input("请输入城市名称: ").strip()
        if not city:
            console_print("请输入有效的城市名称。")
            continue
        if city.lower() in {"quit", "exit", "退出"}:
            return None
        return city


def main():
    console_print(format_health_report(gather_runtime_health()))
    console_print("")
    coordinator = MultiAgentCoordinator()

    while True:
        city = get_city_input()
        if city is None:
            console_print("感谢使用，再见！")
            return

        console_print(f"\n正在查询 {city} 的天气并生成穿衣建议...")
        result = coordinator.process_query(city)
        view_model = build_result_view_model(result)
        console_print(render_cli_report(view_model))

        if result.resolution.need_clarification and result.resolution.clarification_candidates:
            candidate_id = input("\n如需继续，请输入候选 candidate_id；直接回车则跳过: ").strip()
            if candidate_id:
                follow_up = coordinator.process_query(city, selected_candidate_id=candidate_id)
                console_print("")
                console_print(render_cli_report(build_result_view_model(follow_up)))

        continue_query = input("\n是否继续查询其他城市？(y/n): ").strip().lower()
        if continue_query not in {"y", "yes", "是", "继续"}:
            console_print("感谢使用，再见！")
            return


if __name__ == "__main__":
    main()
