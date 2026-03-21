from __future__ import annotations

import importlib
import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv

from app_types import ExecutionRecord, LLMProviderConfig, ModelRegistry
from common_utils import compact_text

load_dotenv()


def is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _read_provider(prefix: str, *, default_name: str, default_provider: str) -> LLMProviderConfig | None:
    api_key = os.environ.get(f"{prefix}API_KEY", "").strip()
    base_url = os.environ.get(f"{prefix}BASE_URL", "").strip()
    model = os.environ.get(f"{prefix}MODEL_ID", "").strip()
    provider = os.environ.get(f"{prefix}PROVIDER", "").strip() or default_provider
    name = os.environ.get(f"{prefix}NAME", "").strip() or default_name

    raw_temperature = os.environ.get(f"{prefix}TEMPERATURE", "").strip() or "0.2"
    raw_timeout = os.environ.get(f"{prefix}TIMEOUT_SECONDS", "").strip() or "60"
    try:
        temperature = float(raw_temperature)
    except ValueError:
        temperature = 0.2
    try:
        timeout_seconds = int(raw_timeout)
    except ValueError:
        timeout_seconds = 60

    if not any([api_key, base_url, model, provider]):
        return None

    missing = [
        field
        for field, value in {
            f"{prefix}API_KEY": api_key,
            f"{prefix}BASE_URL": base_url,
            f"{prefix}MODEL_ID": model,
        }.items()
        if not value
    ]
    return LLMProviderConfig(
        name=name,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        enabled=not missing,
        missing_fields=missing,
    )


def get_model_registry() -> ModelRegistry:
    default_provider = _read_provider("LLM_", default_name="default", default_provider="openai_compatible")
    alternate_provider = _read_provider("ALT_LLM_", default_name="alternate", default_provider="openai_compatible")

    providers: dict[str, LLMProviderConfig] = {}
    default_name = "default"
    if default_provider is not None:
        providers[default_provider.name] = default_provider
        default_name = default_provider.name
    else:
        providers[default_name] = LLMProviderConfig(
            name=default_name,
            provider="openai_compatible",
            enabled=False,
            missing_fields=["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"],
        )

    if alternate_provider is not None:
        providers[alternate_provider.name] = alternate_provider

    requested_default = os.environ.get("DEFAULT_LLM_PROVIDER", "").strip()
    if requested_default and requested_default in providers:
        default_name = requested_default

    return ModelRegistry(default_provider=default_name, providers=providers)


def get_llm_config() -> dict[str, object]:
    registry = get_model_registry()
    default = registry.providers.get(registry.default_provider, LLMProviderConfig(enabled=False))
    return {
        "api_key": default.api_key,
        "base_url": default.base_url,
        "model": default.model,
        "provider": default.provider,
        "provider_name": default.name,
        "enabled": default.enabled,
        "missing_fields": list(default.missing_fields),
        "registry": registry.to_dict(),
    }


def get_dependency_status() -> dict[str, object]:
    config = get_llm_config()
    return {
        "langchain_available": is_module_available("langchain"),
        "langchain_openai_available": is_module_available("langchain_openai"),
        "langchain_core_available": is_module_available("langchain_core"),
        "langgraph_available": is_module_available("langgraph"),
        "fastmcp_available": is_module_available("fastmcp"),
        "llm_configured": config["enabled"],
        "llm_model": config["model"],
        "llm_provider": config["provider"],
        "missing_llm_fields": config["missing_fields"],
        "registry": config["registry"],
    }


def extract_json_payload(text: str) -> object | None:
    if not text:
        return None

    candidates = [text.strip()]
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(segment.strip() for segment in fenced if segment.strip())

    left_curly = text.find("{")
    right_curly = text.rfind("}")
    if 0 <= left_curly < right_curly:
        candidates.append(text[left_curly : right_curly + 1])

    left_square = text.find("[")
    right_square = text.rfind("]")
    if 0 <= left_square < right_square:
        candidates.append(text[left_square : right_square + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _get_provider_config(provider_name: str | None = None) -> LLMProviderConfig:
    registry = get_model_registry()
    name = provider_name or registry.default_provider
    return registry.providers.get(name, registry.providers[registry.default_provider])


def _normalize_response_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                blocks.append(str(item.get("text", "")))
            else:
                blocks.append(str(getattr(item, "text", item)))
        return "".join(blocks).strip()
    return str(content)


def run_agent(
    *,
    role: str,
    name: str,
    system_prompt: str,
    prompt: str,
    provider_name: str | None = None,
    json_mode: bool = False,
) -> tuple[str, ExecutionRecord]:
    start = time.time()
    provider = _get_provider_config(provider_name)
    record = ExecutionRecord(
        role=role,
        name=name,
        node_name=name,
        provider=provider.provider,
        model=provider.model,
        input_summary=compact_text(prompt),
        metadata={
            "framework": "langchain",
            "provider_name": provider.name,
            "json_mode": json_mode,
        },
    )

    if not provider.enabled:
        record.error = "LLM 配置不完整: " + ", ".join(provider.missing_fields)
        record.fallback_used = True
        record.elapsed_ms = int((time.time() - start) * 1000)
        return "", record

    if not is_module_available("langchain_openai"):
        record.error = "未安装 langchain_openai，无法通过 LangChain 调用模型。"
        record.fallback_used = True
        record.elapsed_ms = int((time.time() - start) * 1000)
        return "", record

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url or None,
            temperature=provider.temperature,
            timeout=provider.timeout_seconds,
            max_retries=1,
        )
        response = llm.invoke(
            [
                ("system", system_prompt),
                ("human", prompt),
            ]
        )
        output_text = _normalize_response_content(getattr(response, "content", response))
        record.success = True
        record.used_llm = True
        record.output_summary = compact_text(output_text)
        return output_text, record
    except Exception as exc:
        record.error = str(exc)
        record.fallback_used = True
        return "", record
    finally:
        record.elapsed_ms = int((time.time() - start) * 1000)
