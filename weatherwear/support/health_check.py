from __future__ import annotations

import importlib
import os
import platform
import sys
from importlib import metadata
from typing import Any

from dotenv import load_dotenv

from weatherwear.services.fashion_knowledge import get_vector_index_status
from weatherwear.support.llm_support import get_embedding_health, get_llm_config

load_dotenv()


MODULES = {
    "fastapi": {"required_for": "api_runtime"},
    "pydantic": {"required_for": "api_runtime"},
    "typing_extensions": {"required_for": "api_runtime"},
    "requests": {"required_for": "weather"},
    "langchain": {"required_for": "llm_runtime"},
    "langchain_core": {"required_for": "llm_runtime"},
    "langchain_openai": {"required_for": "provider_runtime"},
    "langgraph": {"required_for": "workflow_runtime"},
    "fastmcp": {"required_for": "mcp_optional"},
}

RECOMMENDED_WEB_STACK = {
    "fastapi": "0.112.2",
    "pydantic": "2.12.5",
    "typing_extensions": "4.15.0",
    "requests": "2.32.5",
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


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _msg(locale: str, key: str, **kwargs: Any) -> str:
    messages = {
        "api_fastapi_high": {
            "zh-CN": "检测到 FastAPI 版本偏高。当前项目建议固定到 `fastapi==0.112.2`。",
            "en-US": "FastAPI is newer than the validated matrix. This project recommends `fastapi==0.112.2`.",
        },
        "api_fastapi_import": {
            "zh-CN": "FastAPI 导入失败，请按 `requirements.txt` 重新安装依赖。",
            "en-US": "FastAPI import failed. Reinstall the dependencies from `requirements.txt`.",
        },
        "pydantic_version": {
            "zh-CN": "当前 Pydantic 版本是 {current}，项目推荐版本是 {expected}。",
            "en-US": "Current Pydantic version is {current}; the recommended version is {expected}.",
        },
        "typing_version": {
            "zh-CN": "当前 typing_extensions 版本与项目推荐矩阵不一致。",
            "en-US": "typing_extensions differs from the validated matrix.",
        },
        "requests_version": {
            "zh-CN": "当前 requests 版本是 {current}，项目推荐版本是 {expected}。",
            "en-US": "Current requests version is {current}; the recommended version is {expected}.",
        },
        "fix_runtime_stack": {
            "zh-CN": "建议执行 `pip install -r requirements.txt --upgrade --force-reinstall` 修复运行时依赖。",
            "en-US": "Run `pip install -r requirements.txt --upgrade --force-reinstall` to repair the runtime stack.",
        },
        "langchain_missing": {
            "zh-CN": "未安装完整的 LangChain 运行栈，LLM 节点会自动走规则兜底。",
            "en-US": "LangChain is missing, so LLM nodes will fall back to rule-based behavior.",
        },
        "langgraph_missing": {
            "zh-CN": "未安装 LangGraph，当前将使用兼容工作流执行器。",
            "en-US": "LangGraph is missing, so the app will use the compatibility workflow runner.",
        },
        "fastmcp_missing": {
            "zh-CN": "未安装 fastmcp，可选 MCP 集成保持关闭状态。",
            "en-US": "fastmcp is missing, so the optional MCP integration stays disabled.",
        },
        "llm_missing": {
            "zh-CN": "LLM 环境变量不完整：{missing}",
            "en-US": "LLM environment variables are incomplete: {missing}",
        },
        "weather_missing": {
            "zh-CN": "未配置 OPENWEATHER_API_KEY，天气只能使用 demo 模式或返回错误。",
            "en-US": "OPENWEATHER_API_KEY is missing, so weather data can only use demo mode or fail.",
        },
        "python": {"zh-CN": "Python", "en-US": "Python"},
        "platform": {"zh-CN": "平台", "en-US": "Platform"},
        "llm_ready": {"zh-CN": "LLM 配置完整", "en-US": "LLM configured"},
        "weather_ready": {"zh-CN": "OpenWeather 已配置", "en-US": "OpenWeather configured"},
        "web_ready": {"zh-CN": "运行栈兼容", "en-US": "Runtime stack compatible"},
        "yes": {"zh-CN": "是", "en-US": "Yes"},
        "no": {"zh-CN": "否", "en-US": "No"},
        "modules": {"zh-CN": "模块状态:", "en-US": "Modules:"},
        "recommended": {"zh-CN": "推荐运行时依赖矩阵:", "en-US": "Recommended runtime dependency matrix:"},
        "issues": {"zh-CN": "兼容性提示:", "en-US": "Compatibility notes:"},
        "suggestions": {"zh-CN": "建议:", "en-US": "Suggestions:"},
    }
    locale_key = "en-US" if _is_english(locale) else "zh-CN"
    return messages[key][locale_key].format(**kwargs)


def evaluate_web_stack(modules: dict[str, dict[str, Any]], locale: str = "zh-CN") -> dict[str, Any]:
    issues: list[str] = []
    compatible = True

    for module_name in ("fastapi", "pydantic", "typing_extensions", "requests"):
        if not modules.get(module_name, {}).get("available", False):
            compatible = False

    fastapi_info = modules.get("fastapi", {})
    pydantic_info = modules.get("pydantic", {})
    typing_info = modules.get("typing_extensions", {})
    requests_info = modules.get("requests", {})

    fastapi_version = fastapi_info.get("version", "")
    if fastapi_version and _parse_version(fastapi_version) >= (0, 113):
        compatible = False
        issues.append(_msg(locale, "api_fastapi_high"))
    if "unsupported operand type(s) for |" in fastapi_info.get("error", ""):
        compatible = False
        issues.append(_msg(locale, "api_fastapi_import"))

    if pydantic_info.get("version") and pydantic_info["version"] != RECOMMENDED_WEB_STACK["pydantic"]:
        issues.append(
            _msg(
                locale,
                "pydantic_version",
                current=pydantic_info["version"],
                expected=RECOMMENDED_WEB_STACK["pydantic"],
            )
        )
    if typing_info.get("version") and typing_info["version"] != RECOMMENDED_WEB_STACK["typing_extensions"]:
        issues.append(_msg(locale, "typing_version"))
    if requests_info.get("version") and requests_info["version"] != RECOMMENDED_WEB_STACK["requests"]:
        issues.append(
            _msg(
                locale,
                "requests_version",
                current=requests_info["version"],
                expected=RECOMMENDED_WEB_STACK["requests"],
            )
        )

    return {
        "compatible": compatible,
        "issues": issues,
        "recommended": dict(RECOMMENDED_WEB_STACK),
    }


def gather_runtime_health(locale: str = "zh-CN") -> dict[str, Any]:
    modules = {name: _check_module(name) for name in MODULES}
    llm_config = get_llm_config()
    llm_missing = [
        name
        for name in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"]
        if not os.environ.get(name, "").strip()
    ]
    openweather_configured = bool(os.environ.get("OPENWEATHER_API_KEY", "").strip())
    web_stack = evaluate_web_stack(modules, locale=locale)
    embedding_health = get_embedding_health()
    index_status = get_vector_index_status()
    embedding_health["index_compatible"] = index_status.get("index_compatible")

    suggestions: list[str] = []
    if not web_stack["compatible"]:
        suggestions.extend(web_stack["issues"])
        suggestions.append(_msg(locale, "fix_runtime_stack"))
    if not modules["langchain"]["available"] or not modules["langchain_openai"]["available"]:
        suggestions.append(_msg(locale, "langchain_missing"))
    if not modules["langgraph"]["available"]:
        suggestions.append(_msg(locale, "langgraph_missing"))
    if not modules["fastmcp"]["available"]:
        suggestions.append(_msg(locale, "fastmcp_missing"))
    if llm_missing:
        suggestions.append(_msg(locale, "llm_missing", missing=", ".join(llm_missing)))
    if not openweather_configured:
        suggestions.append(_msg(locale, "weather_missing"))

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "workspace_root": os.path.abspath(os.getcwd()),
        "modules": modules,
        "llm_configured": not llm_missing,
        "llm_provider": llm_config.get("provider_name") or llm_config.get("provider", ""),
        "llm_model": llm_config.get("model", ""),
        "missing_llm_fields": llm_missing,
        "openweather_configured": openweather_configured,
        "embedding_health": embedding_health,
        "embedding_index": index_status,
        "web_stack": web_stack,
        "suggestions": suggestions,
    }


def format_health_report(health: dict[str, Any], locale: str = "zh-CN") -> str:
    web_stack = health.get("web_stack", {})
    recommended = web_stack.get("recommended", {})
    lines = [
        f"{_msg(locale, 'python')}: {health['python_version']}",
        f"{_msg(locale, 'platform')}: {health['platform']}",
        f"{_msg(locale, 'llm_ready')}: {_msg(locale, 'yes') if health['llm_configured'] else _msg(locale, 'no')}",
        f"{_msg(locale, 'weather_ready')}: {_msg(locale, 'yes') if health['openweather_configured'] else _msg(locale, 'no')}",
        f"{_msg(locale, 'web_ready')}: {_msg(locale, 'yes') if web_stack.get('compatible') else _msg(locale, 'no')}",
        "",
        _msg(locale, "modules"),
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
                _msg(locale, "recommended"),
                f"- fastapi=={recommended.get('fastapi', '')}",
                f"- pydantic=={recommended.get('pydantic', '')}",
                f"- typing_extensions=={recommended.get('typing_extensions', '')}",
                f"- requests=={recommended.get('requests', '')}",
            ]
        )

    issues = web_stack.get("issues", [])
    if issues:
        lines.append("")
        lines.append(_msg(locale, "issues"))
        lines.extend(f"- {item}" for item in issues)

    if health["suggestions"]:
        lines.append("")
        lines.append(_msg(locale, "suggestions"))
        lines.extend(f"- {item}" for item in health["suggestions"])

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_health_report(gather_runtime_health()))
