from __future__ import annotations

import importlib
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

from weatherwear.domain.types import ExecutionRecord, LLMProviderConfig, ModelRegistry
from weatherwear.support.common_utils import compact_text
from weatherwear.support.env_manager import env_manager

load_dotenv()


_EMBEDDING_HEALTH_CACHE: dict[str, Any] = {
    "status": "unknown",
    "provider": "",
    "model": "",
    "dimensions": 0,
    "latency_ms": 0,
    "index_compatible": None,
    "degrade_reason": "",
    "last_checked_at": "",
    "embedding_fingerprint": "",
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def refresh_env(*, override: bool = False) -> None:
    load_dotenv(dotenv_path=env_manager.env_file, override=override)


def is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _read_provider(
    prefix: str,
    *,
    default_name: str,
    default_provider: str,
) -> LLMProviderConfig | None:
    api_key = env_manager.get_value(f"{prefix}API_KEY", "") or ""
    base_url = env_manager.get_value(f"{prefix}BASE_URL", "") or ""
    model = env_manager.get_value(f"{prefix}MODEL_ID", "") or ""
    provider = env_manager.get_value(f"{prefix}PROVIDER", "") or default_provider
    name = env_manager.get_value(f"{prefix}NAME", "") or default_name
    proxy_url = env_manager.get_value(f"{prefix}PROXY_URL", "") or ""

    raw_temperature = env_manager.get_value(f"{prefix}TEMPERATURE", "0.2") or "0.2"
    raw_timeout = env_manager.get_value(f"{prefix}TIMEOUT_SECONDS", "60") or "60"
    try:
        temperature = float(raw_temperature)
    except ValueError:
        temperature = 0.2
    try:
        timeout_seconds = int(raw_timeout)
    except ValueError:
        timeout_seconds = 60

    if not any([api_key, base_url, model, provider, proxy_url]):
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
        proxy_url=proxy_url,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        enabled=not missing,
        missing_fields=missing,
    )


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _read_embedding_settings(default_provider: LLMProviderConfig | None = None) -> dict[str, Any]:
    inherit_from_chat = _as_bool(env_manager.get_value("EMBEDDING_INHERIT_FROM_CHAT_PROVIDER", "0"), False)
    raw_enabled = env_manager.get_value("EMBEDDING_ENABLED", "")
    explicit_enabled = _as_bool(raw_enabled, False) if raw_enabled != "" else None
    provider = (env_manager.get_value("EMBEDDING_PROVIDER", "") or "").strip()
    base_url = (env_manager.get_value("EMBEDDING_BASE_URL", "") or "").strip()
    model = (env_manager.get_value("EMBEDDING_MODEL", "") or "").strip()
    proxy_url = (env_manager.get_value("EMBEDDING_PROXY_URL", "") or "").strip()
    api_key = (env_manager.get_value("EMBEDDING_API_KEY", "") or "").strip()
    timeout_raw = env_manager.get_value("EMBEDDING_TIMEOUT_SECONDS", "60") or "60"
    try:
        timeout_seconds = int(timeout_raw)
    except ValueError:
        timeout_seconds = 60

    inherited = default_provider or LLMProviderConfig(enabled=False)
    if inherit_from_chat:
        provider = provider or inherited.provider or "openai_compatible"
        base_url = base_url or inherited.base_url
        proxy_url = proxy_url or inherited.proxy_url
        api_key = api_key or inherited.api_key

    missing_fields = [field for field, value in {"base_url": base_url, "model": model, "api_key": api_key}.items() if not value]
    enabled = bool(explicit_enabled) if explicit_enabled is not None else bool(model)
    enabled = bool(enabled and not missing_fields)
    return {
        "enabled": enabled,
        "inherit_from_chat_provider": inherit_from_chat,
        "provider": provider or "openai_compatible",
        "base_url": base_url,
        "model": model,
        "proxy_url": proxy_url,
        "timeout_seconds": timeout_seconds,
        "api_key": api_key,
        "missing_fields": missing_fields,
    }


def _embedding_fingerprint(config: dict[str, Any], dimensions: int | None = None) -> str:
    payload = {
        "provider": str(config.get("provider", "") or ""),
        "base_url": str(config.get("base_url", "") or ""),
        "model": str(config.get("model", "") or ""),
        "dimensions": int(dimensions or 0),
    }
    return compact_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), max_len=240)


def get_model_registry() -> ModelRegistry:
    refresh_env(override=False)
    default_provider = _read_provider(
        "LLM_",
        default_name="default",
        default_provider="openai_compatible",
    )
    alternate_provider = _read_provider(
        "ALT_LLM_",
        default_name="alternate",
        default_provider="openai_compatible",
    )

    providers: dict[str, LLMProviderConfig] = {}
    default_slot = "default"
    if default_provider is not None:
        providers["default"] = default_provider
    else:
        providers["default"] = LLMProviderConfig(
            name="default",
            provider="openai_compatible",
            enabled=False,
            missing_fields=["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"],
        )

    if alternate_provider is not None:
        providers["alternate"] = alternate_provider
    else:
        providers["alternate"] = LLMProviderConfig(
            name="alternate",
            provider="openai_compatible",
            enabled=False,
            missing_fields=["ALT_LLM_API_KEY", "ALT_LLM_BASE_URL", "ALT_LLM_MODEL_ID"],
        )

    requested_default = env_manager.get_value("DEFAULT_LLM_PROVIDER", "") or ""
    normalized_default = _normalize_slot(requested_default) if requested_default else "default"
    if normalized_default in providers:
        default_slot = normalized_default

    embedding = _read_embedding_settings(providers.get(default_slot))
    return ModelRegistry(default_provider=default_slot, providers=providers, embedding=embedding)


def get_llm_config() -> dict[str, object]:
    registry = get_model_registry()
    default = registry.providers.get(registry.default_provider, LLMProviderConfig(enabled=False))
    return {
        "api_key": default.api_key,
        "base_url": default.base_url,
        "model": default.model,
        "provider": default.provider,
        "provider_name": default.name,
        "proxy_url": default.proxy_url,
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


def serialize_provider_public(provider: LLMProviderConfig) -> dict[str, Any]:
    return {
        "name": provider.name,
        "provider": provider.provider,
        "base_url": provider.base_url,
        "model": provider.model,
        "proxy_url": provider.proxy_url,
        "temperature": provider.temperature,
        "timeout_seconds": provider.timeout_seconds,
        "enabled": provider.enabled,
        "missing_fields": list(provider.missing_fields),
        "has_api_key": bool(provider.api_key),
    }


def build_model_settings_response() -> dict[str, Any]:
    registry = get_model_registry()
    embedding_runtime = resolve_embedding_runtime_config()
    embedding_health = get_embedding_health()
    return {
        "default_provider": registry.default_provider,
        "active_provider": registry.default_provider,
        "providers": {
            slot: serialize_provider_public(provider)
            for slot, provider in registry.providers.items()
        },
        "embedding": {
            "enabled": bool(registry.embedding.get("enabled", False)),
            "inherit_from_chat_provider": bool(registry.embedding.get("inherit_from_chat_provider", False)),
            "provider": str(registry.embedding.get("provider", "openai_compatible") or "openai_compatible"),
            "base_url": str(registry.embedding.get("base_url", "") or ""),
            "model": str(registry.embedding.get("model", "") or ""),
            "proxy_url": str(registry.embedding.get("proxy_url", "") or ""),
            "timeout_seconds": int(registry.embedding.get("timeout_seconds", 60) or 60),
            "missing_fields": list(registry.embedding.get("missing_fields", [])),
            "has_api_key": bool(registry.embedding.get("api_key", "")),
            "runtime_provider": str(embedding_runtime.get("runtime_provider", "") or ""),
            "runtime_base_url": str(embedding_runtime.get("runtime_base_url", "") or ""),
            "runtime_proxy_url": str(embedding_runtime.get("runtime_proxy_url", "") or ""),
            "embedding_fingerprint": str(embedding_runtime.get("embedding_fingerprint", "") or ""),
            "health": embedding_health,
        },
    }


def _normalize_slot(slot: str) -> str:
    return "alternate" if str(slot).strip().lower() == "alternate" else "default"


def _slot_prefix(slot: str) -> str:
    return "ALT_LLM_" if _normalize_slot(slot) == "alternate" else "LLM_"


def update_model_settings(
    *,
    slot: str,
    payload: dict[str, Any],
    clear_api_key: bool = False,
    clear_embedding_api_key: bool = False,
) -> dict[str, Any]:
    normalized_slot = _normalize_slot(slot)
    prefix = _slot_prefix(normalized_slot)
    updates: dict[str, str] = {}
    deletions: list[str] = []

    mapping = {
        "name": "NAME",
        "provider": "PROVIDER",
        "base_url": "BASE_URL",
        "model": "MODEL_ID",
        "proxy_url": "PROXY_URL",
        "temperature": "TEMPERATURE",
        "timeout_seconds": "TIMEOUT_SECONDS",
    }
    for field, suffix in mapping.items():
        if field not in payload:
            continue
        value = payload[field]
        key = f"{prefix}{suffix}"
        if value is None or str(value).strip() == "":
            updates[key] = ""
        else:
            updates[key] = str(value).strip()

    api_key = payload.get("api_key")
    if api_key is not None and str(api_key).strip():
        updates[f"{prefix}API_KEY"] = str(api_key).strip()
    elif clear_api_key:
        updates[f"{prefix}API_KEY"] = ""

    if "default_provider" in payload and str(payload["default_provider"]).strip():
        updates["DEFAULT_LLM_PROVIDER"] = _normalize_slot(str(payload["default_provider"]).strip())

    embedding_payload = payload.get("embedding")
    if isinstance(embedding_payload, dict):
        embedding_mapping = {
            "enabled": "EMBEDDING_ENABLED",
            "inherit_from_chat_provider": "EMBEDDING_INHERIT_FROM_CHAT_PROVIDER",
            "provider": "EMBEDDING_PROVIDER",
            "base_url": "EMBEDDING_BASE_URL",
            "model": "EMBEDDING_MODEL",
            "proxy_url": "EMBEDDING_PROXY_URL",
            "timeout_seconds": "EMBEDDING_TIMEOUT_SECONDS",
        }
        for field, env_key in embedding_mapping.items():
            if field not in embedding_payload:
                continue
            value = embedding_payload[field]
            if isinstance(value, bool):
                updates[env_key] = "1" if value else "0"
            elif value is None:
                updates[env_key] = ""
            else:
                updates[env_key] = str(value).strip()

        embedding_api_key = embedding_payload.get("api_key")
        if embedding_api_key is not None and str(embedding_api_key).strip():
            updates["EMBEDDING_API_KEY"] = str(embedding_api_key).strip()
        elif clear_embedding_api_key:
            updates["EMBEDDING_API_KEY"] = ""

    if not env_manager.apply_changes(updates=updates, deletions=deletions):
        raise RuntimeError("更新模型配置失败")
    refresh_env(override=True)
    return build_model_settings_response()


@contextmanager
def _temporary_proxy_env(proxy_url: str):
    if not proxy_url:
        yield
        return

    previous_http = os.environ.get("HTTP_PROXY")
    previous_https = os.environ.get("HTTPS_PROXY")
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    try:
        yield
    finally:
        if previous_http is None:
            os.environ.pop("HTTP_PROXY", None)
        else:
            os.environ["HTTP_PROXY"] = previous_http
        if previous_https is None:
            os.environ.pop("HTTPS_PROXY", None)
        else:
            os.environ["HTTPS_PROXY"] = previous_https


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


def run_agent_with_provider_config(
    *,
    provider_config: LLMProviderConfig,
    role: str,
    name: str,
    system_prompt: str,
    prompt: str,
    json_mode: bool = False,
    cancel_token: object | None = None,
) -> tuple[str, ExecutionRecord]:
    start = time.time()
    record = ExecutionRecord(
        role=role,
        name=name,
        node_name=name,
        provider=provider_config.provider,
        model=provider_config.model,
        input_summary=compact_text(prompt),
        metadata={
            "framework": "langchain",
            "provider_name": provider_config.name,
            "json_mode": json_mode,
        },
    )

    if cancel_token and hasattr(cancel_token, "raise_if_cancelled"):
        cancel_token.raise_if_cancelled(f"llm:{name}:before")

    if not provider_config.enabled:
        record.error = "LLM 配置不完整: " + ", ".join(provider_config.missing_fields)
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

        with _temporary_proxy_env(provider_config.proxy_url):
            llm = ChatOpenAI(
                model=provider_config.model,
                api_key=provider_config.api_key,
                base_url=provider_config.base_url or None,
                temperature=provider_config.temperature,
                timeout=provider_config.timeout_seconds,
                max_retries=1,
            )
            response = llm.invoke(
                [
                    ("system", system_prompt),
                    ("human", prompt),
                ]
            )
        if cancel_token and hasattr(cancel_token, "raise_if_cancelled"):
            cancel_token.raise_if_cancelled(f"llm:{name}:after")
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


def run_agent(
    *,
    role: str,
    name: str,
    system_prompt: str,
    prompt: str,
    provider_name: str | None = None,
    json_mode: bool = False,
    cancel_token: object | None = None,
) -> tuple[str, ExecutionRecord]:
    provider = _get_provider_config(provider_name)
    return run_agent_with_provider_config(
        provider_config=provider,
        role=role,
        name=name,
        system_prompt=system_prompt,
        prompt=prompt,
        json_mode=json_mode,
        cancel_token=cancel_token,
    )


def test_model_provider(
    *,
    slot: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slot_name = _normalize_slot(slot)
    registry = get_model_registry()
    current = registry.providers.get(slot_name, LLMProviderConfig(name=slot_name))
    payload = payload or {}
    raw_api_key = payload.get("api_key")
    merged_api_key = current.api_key if raw_api_key is None or str(raw_api_key).strip() == "" else str(raw_api_key).strip()
    merged = LLMProviderConfig(
        name=str(payload.get("name", current.name or slot_name)).strip() or slot_name,
        provider=str(payload.get("provider", current.provider or "openai_compatible")).strip() or "openai_compatible",
        api_key=merged_api_key,
        base_url=str(payload.get("base_url", current.base_url)).strip(),
        model=str(payload.get("model", current.model)).strip(),
        proxy_url=str(payload.get("proxy_url", current.proxy_url)).strip(),
        temperature=float(payload.get("temperature", current.temperature or 0.2)),
        timeout_seconds=int(payload.get("timeout_seconds", current.timeout_seconds or 60)),
    )
    merged.missing_fields = [
        field
        for field, value in {
            "api_key": merged.api_key,
            "base_url": merged.base_url,
            "model": merged.model,
        }.items()
        if not value
    ]
    merged.enabled = not merged.missing_fields

    output, record = run_agent_with_provider_config(
        provider_config=merged,
        role="模型连通性测试",
        name="ModelConnectionCheck",
        system_prompt="Reply with OK only.",
        prompt="Ping",
    )
    ok = record.success and bool(output.strip())
    message = "连接成功" if ok else (record.error or "连接失败")
    return {
        "ok": ok,
        "message": message,
        "provider": merged.provider,
        "model": merged.model,
        "latency_ms": record.elapsed_ms,
    }


def get_embedding_config() -> dict[str, Any]:
    registry = get_model_registry()
    return dict(registry.embedding)


def _cache_embedding_health(payload: dict[str, Any]) -> dict[str, Any]:
    _EMBEDDING_HEALTH_CACHE.clear()
    _EMBEDDING_HEALTH_CACHE.update(payload)
    return dict(_EMBEDDING_HEALTH_CACHE)


def resolve_embedding_runtime_config(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = get_model_registry()
    current = dict(registry.embedding)
    payload = payload or {}
    raw_api_key = payload.get("api_key")
    api_key = current.get("api_key", "") if raw_api_key is None or str(raw_api_key).strip() == "" else str(raw_api_key).strip()
    enabled = _as_bool(payload.get("enabled", current.get("enabled", False)), bool(current.get("enabled", False)))
    inherit_from_chat = _as_bool(
        payload.get("inherit_from_chat_provider", current.get("inherit_from_chat_provider", False)),
        bool(current.get("inherit_from_chat_provider", False)),
    )
    provider = str(payload.get("provider", current.get("provider", "openai_compatible")) or "openai_compatible")
    base_url = str(payload.get("base_url", current.get("base_url", "")) or "")
    proxy_url = str(payload.get("proxy_url", current.get("proxy_url", "")) or "")
    if inherit_from_chat:
        active_provider = registry.providers.get(registry.default_provider, LLMProviderConfig(enabled=False))
        provider = provider or active_provider.provider or "openai_compatible"
        base_url = base_url or active_provider.base_url
        proxy_url = proxy_url or active_provider.proxy_url
        api_key = api_key or active_provider.api_key
    merged = {
        "enabled": enabled,
        "inherit_from_chat_provider": inherit_from_chat,
        "provider": provider,
        "base_url": base_url,
        "model": str(payload.get("model", current.get("model", "")) or ""),
        "proxy_url": proxy_url,
        "timeout_seconds": int(payload.get("timeout_seconds", current.get("timeout_seconds", 60)) or 60),
        "api_key": api_key,
        "runtime_provider": provider,
        "runtime_base_url": base_url,
        "runtime_proxy_url": proxy_url,
    }
    merged["missing_fields"] = [
        field
        for field, value in {"base_url": merged["base_url"], "model": merged["model"], "api_key": merged["api_key"]}.items()
        if not value
    ]
    merged["embedding_fingerprint"] = _embedding_fingerprint(merged)
    return merged


def get_embedding_health(*, force: bool = False) -> dict[str, Any]:
    if not force and _EMBEDDING_HEALTH_CACHE.get("last_checked_at"):
        return dict(_EMBEDDING_HEALTH_CACHE)
    return probe_embedding_health(force=force)


def probe_embedding_health(*, force: bool = False) -> dict[str, Any]:
    current = resolve_embedding_runtime_config()
    if not current.get("enabled"):
        return _cache_embedding_health(
            {
                "status": "disabled",
                "provider": str(current.get("runtime_provider", "") or ""),
                "model": str(current.get("model", "") or ""),
                "dimensions": 0,
                "latency_ms": 0,
                "index_compatible": None,
                "degrade_reason": "embedding_disabled",
                "last_checked_at": _utc_now_iso(),
                "embedding_fingerprint": str(current.get("embedding_fingerprint", "") or ""),
            }
        )
    if current.get("missing_fields"):
        return _cache_embedding_health(
            {
                "status": "degraded",
                "provider": str(current.get("runtime_provider", "") or ""),
                "model": str(current.get("model", "") or ""),
                "dimensions": 0,
                "latency_ms": 0,
                "index_compatible": None,
                "degrade_reason": "embedding_config_incomplete",
                "missing_fields": list(current.get("missing_fields", [])),
                "last_checked_at": _utc_now_iso(),
                "embedding_fingerprint": str(current.get("embedding_fingerprint", "") or ""),
            }
        )

    probe_payload = dict(current)
    probe_payload["timeout_seconds"] = min(int(current.get("timeout_seconds", 60) or 60), 8)
    vectors, info = embed_texts(["WeatherWear embedding startup probe."], payload=probe_payload)
    dimensions = len(vectors[0]) if vectors else int(info.get("dimensions", 0) or 0)
    status = "healthy" if info.get("ok") and dimensions else "degraded"
    return _cache_embedding_health(
        {
            "status": status,
            "provider": str(info.get("provider", current.get("runtime_provider", "")) or ""),
            "model": str(info.get("model", current.get("model", "")) or ""),
            "dimensions": dimensions,
            "latency_ms": int(info.get("elapsed_ms", 0) or 0),
            "index_compatible": None,
            "degrade_reason": "" if status == "healthy" else str(info.get("error") or "embedding_probe_failed"),
            "last_checked_at": _utc_now_iso(),
            "embedding_fingerprint": str(info.get("embedding_fingerprint", current.get("embedding_fingerprint", "")) or ""),
        }
    )


def embed_texts(
    texts: list[str],
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[list[list[float]], dict[str, Any]]:
    merged = resolve_embedding_runtime_config(payload)
    if not merged["enabled"]:
        return [], {"ok": False, "fallback_used": True, "error": "embedding_disabled", **merged}
    if merged["missing_fields"]:
        return [], {"ok": False, "fallback_used": True, "error": "embedding_config_incomplete", **merged}
    if not is_module_available("langchain_openai"):
        return [], {"ok": False, "fallback_used": True, "error": "langchain_openai_missing", **merged}

    start = time.time()
    try:
        from langchain_openai import OpenAIEmbeddings

        with _temporary_proxy_env(str(merged["proxy_url"] or "")):
            embeddings = OpenAIEmbeddings(
                model=str(merged["model"]),
                api_key=str(merged["api_key"]),
                base_url=str(merged["base_url"]) or None,
                request_timeout=int(merged["timeout_seconds"]),
                max_retries=1,
            )
            vectors = embeddings.embed_documents(texts)
        dimensions = len(vectors[0]) if vectors else 0
        return vectors, {
            "ok": True,
            "fallback_used": False,
            "provider": merged["provider"],
            "model": merged["model"],
            "elapsed_ms": int((time.time() - start) * 1000),
            "dimensions": dimensions,
            "embedding_fingerprint": _embedding_fingerprint(merged, dimensions),
        }
    except Exception as exc:
        return [], {
            "ok": False,
            "fallback_used": True,
            "error": str(exc),
            "dimensions": 0,
            "embedding_fingerprint": str(merged.get("embedding_fingerprint", "") or ""),
            **merged,
        }


def test_embedding_provider(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    vectors, info = embed_texts(["WeatherWear embedding probe. Use only for connection testing."], payload=payload)
    ok = bool(info.get("ok")) and bool(vectors)
    dimensions = len(vectors[0]) if vectors else int(info.get("dimensions", 0) or 0)
    return {
        "ok": ok,
        "message": "连接成功" if ok else str(info.get("error") or "连接失败"),
        "provider": str(info.get("provider", "openai_compatible") or "openai_compatible"),
        "model": str(info.get("model", "") or ""),
        "latency_ms": int(info.get("elapsed_ms", 0) or 0),
        "dimensions": dimensions,
        "index_compatible": None,
        "degrade_reason": "" if ok else str(info.get("error") or "embedding_test_failed"),
        "embedding_fingerprint": str(info.get("embedding_fingerprint", "") or ""),
    }

