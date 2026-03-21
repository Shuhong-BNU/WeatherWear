from __future__ import annotations

import importlib
import os
import platform
import sys
from importlib import metadata
from typing import Any

from dotenv import load_dotenv

load_dotenv()


MODULES = {
    "gradio": {"required_for": "web_ui"},
    "fastapi": {"required_for": "web_ui"},
    "pydantic": {"required_for": "web_ui"},
    "typing_extensions": {"required_for": "web_ui"},
    "huggingface_hub": {"required_for": "web_ui"},
    "langchain": {"required_for": "llm_runtime"},
    "langchain_core": {"required_for": "llm_runtime"},
    "langchain_openai": {"required_for": "provider_runtime"},
    "langgraph": {"required_for": "workflow_runtime"},
    "fastmcp": {"required_for": "mcp_optional"},
    "requests": {"required_for": "weather"},
}

RECOMMENDED_WEB_STACK = {
    "gradio": "4.44.1",
    "fastapi": "0.112.2",
    "pydantic": "2.12.5",
    "typing_extensions": "4.15.0",
    "huggingface_hub": "0.36.2",
}


def _safe_version(module_name: str) -> str:
    try:
        return metadata.version(module_name)
    except metadata.PackageNotFoundError:
        return ""
    except Exception:
        return ""


def _parse_version(version_text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in version_text.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _check_module(module_name: str) -> dict[str, Any]:
    installed_version = _safe_version(module_name)
    try:
        module = importlib.import_module(module_name)
        return {
            "available": True,
            "version": getattr(module, "__version__", "") or installed_version,
            "installed_version": installed_version,
            "error": "",
        }
    except Exception as exc:
        return {
            "available": False,
            "version": installed_version,
            "installed_version": installed_version,
            "error": f"{type(exc).__name__}: {exc}",
        }


def evaluate_web_stack(modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    compatible = True

    for module_name in ("gradio", "fastapi", "pydantic", "typing_extensions", "huggingface_hub"):
        if not modules.get(module_name, {}).get("available", False):
            compatible = False

    fastapi_info = modules.get("fastapi", {})
    pydantic_info = modules.get("pydantic", {})
    typing_extensions_info = modules.get("typing_extensions", {})
    huggingface_hub_info = modules.get("huggingface_hub", {})
    gradio_info = modules.get("gradio", {})

    fastapi_version = fastapi_info.get("version", "")
    if fastapi_version and _parse_version(fastapi_version) >= (0, 113):
        compatible = False
        issues.append(
            "检测到 FastAPI 版本偏高。当前项目在 `gradio==4.44.1` 下建议固定到 `fastapi==0.112.2`。"
        )
    if "unsupported operand type(s) for |" in fastapi_info.get("error", ""):
        compatible = False
        issues.append("FastAPI 导入失败，命中当前 Web 栈已知兼容性问题。请按 requirements-web.txt 重装。")

    if gradio_info.get("version") and gradio_info["version"] != RECOMMENDED_WEB_STACK["gradio"]:
        issues.append(
            f"当前 Gradio 版本是 {gradio_info['version']}，项目推荐版本是 {RECOMMENDED_WEB_STACK['gradio']}。"
        )
    if pydantic_info.get("version") and pydantic_info["version"] != RECOMMENDED_WEB_STACK["pydantic"]:
        issues.append(
            f"当前 Pydantic 版本是 {pydantic_info['version']}，项目推荐版本是 {RECOMMENDED_WEB_STACK['pydantic']}。"
        )
    if typing_extensions_info.get("version") and typing_extensions_info["version"] != RECOMMENDED_WEB_STACK["typing_extensions"]:
        issues.append("当前 typing_extensions 版本与项目推荐矩阵不一致，如 Web UI 导入异常建议按矩阵重装。")
    huggingface_hub_version = huggingface_hub_info.get("version", "")
    if huggingface_hub_version and _parse_version(huggingface_hub_version) >= (1, 0):
        compatible = False
        issues.append("当前 huggingface_hub 版本过高。Gradio 4.44.1 仍依赖 0.x 系列，建议降级。")
    elif huggingface_hub_version and huggingface_hub_version != RECOMMENDED_WEB_STACK["huggingface_hub"]:
        issues.append(
            f"当前 huggingface_hub 版本是 {huggingface_hub_version}，项目推荐版本是 {RECOMMENDED_WEB_STACK['huggingface_hub']}。"
        )

    return {
        "compatible": compatible,
        "issues": issues,
        "recommended": dict(RECOMMENDED_WEB_STACK),
    }


def gather_runtime_health() -> dict[str, Any]:
    modules = {name: _check_module(name) for name in MODULES}
    llm_missing = [
        name
        for name in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"]
        if not os.environ.get(name, "").strip()
    ]
    openweather_configured = bool(os.environ.get("OPENWEATHER_API_KEY", "").strip())
    web_stack = evaluate_web_stack(modules)

    suggestions: list[str] = []
    if not web_stack["compatible"]:
        suggestions.extend(web_stack["issues"])
        suggestions.append("建议执行 `pip install -r requirements-web.txt --upgrade --force-reinstall` 修复 Web UI 依赖。")
    if not modules["langchain"]["available"] or not modules["langchain_openai"]["available"]:
        suggestions.append("未安装 LangChain 运行栈，LLM 节点会自动走规则兜底。")
    if not modules["langgraph"]["available"]:
        suggestions.append("未安装 LangGraph，当前将使用兼容工作流执行器；安装后会自动切到 LangGraph。")
    if not modules["fastmcp"]["available"]:
        suggestions.append("未安装 fastmcp，MCP 天气服务保持可选关闭状态。")
    if llm_missing:
        suggestions.append("LLM 环境变量不完整：" + ", ".join(llm_missing))
    if not openweather_configured:
        suggestions.append("未配置 OPENWEATHER_API_KEY，天气只可使用 demo 模式或错误返回。")

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "modules": modules,
        "llm_configured": not llm_missing,
        "missing_llm_fields": llm_missing,
        "openweather_configured": openweather_configured,
        "web_stack": web_stack,
        "suggestions": suggestions,
    }


def format_health_report(health: dict[str, Any]) -> str:
    web_stack = health.get("web_stack", {})
    recommended = web_stack.get("recommended", {})
    lines = [
        f"Python: {health['python_version']}",
        f"Platform: {health['platform']}",
        f"LLM 配置完整: {'是' if health['llm_configured'] else '否'}",
        f"OpenWeather 已配置: {'是' if health['openweather_configured'] else '否'}",
        f"Web 栈兼容: {'是' if web_stack.get('compatible') else '否'}",
        "",
        "模块状态:",
    ]

    for name, info in health["modules"].items():
        status = "OK" if info["available"] else "ERROR"
        suffix = f" ({info['version']})" if info["version"] else ""
        line = f"- {name}: {status}{suffix}"
        if info["error"]:
            line += f" -> {info['error']}"
        lines.append(line)

    if recommended:
        lines.extend(
            [
                "",
                "推荐 Web 依赖矩阵:",
                f"- gradio=={recommended.get('gradio', '')}",
                f"- fastapi=={recommended.get('fastapi', '')}",
                f"- pydantic=={recommended.get('pydantic', '')}",
                f"- typing_extensions=={recommended.get('typing_extensions', '')}",
                f"- huggingface_hub=={recommended.get('huggingface_hub', '')}",
            ]
        )

    issues = web_stack.get("issues", [])
    if issues:
        lines.append("")
        lines.append("兼容性提示:")
        lines.extend(f"- {item}" for item in issues)

    if health["suggestions"]:
        lines.append("")
        lines.append("建议:")
        lines.extend(f"- {item}" for item in health["suggestions"])

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_health_report(gather_runtime_health()))
