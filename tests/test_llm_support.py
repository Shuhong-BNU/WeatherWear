from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import llm_support


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeChatOpenAI:
    last_kwargs = {}
    last_messages = None

    def __init__(self, **kwargs):
        FakeChatOpenAI.last_kwargs = kwargs

    def invoke(self, messages):
        FakeChatOpenAI.last_messages = messages
        return FakeResponse("ok")


class LLMSupportTests(unittest.TestCase):
    def test_model_registry_supports_default_and_alternate_provider(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "default-key",
                "LLM_BASE_URL": "https://default.example/v1",
                "LLM_MODEL_ID": "gpt-4o-mini",
                "ALT_LLM_NAME": "alternate",
                "ALT_LLM_PROVIDER": "openai_compatible",
                "ALT_LLM_API_KEY": "alt-key",
                "ALT_LLM_BASE_URL": "https://alt.example/v1",
                "ALT_LLM_MODEL_ID": "qwen-max",
            },
            clear=False,
        ):
            registry = llm_support.get_model_registry()
        self.assertIn("default", registry.providers)
        self.assertIn("alternate", registry.providers)
        self.assertEqual(registry.providers["alternate"].model, "qwen-max")

    def test_run_agent_can_switch_provider_name(self):
        fake_module = types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI)
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai_compatible",
                "LLM_API_KEY": "default-key",
                "LLM_BASE_URL": "https://default.example/v1",
                "LLM_MODEL_ID": "gpt-4o-mini",
                "ALT_LLM_NAME": "alternate",
                "ALT_LLM_PROVIDER": "openai_compatible",
                "ALT_LLM_API_KEY": "alt-key",
                "ALT_LLM_BASE_URL": "https://alt.example/v1",
                "ALT_LLM_MODEL_ID": "qwen-max",
            },
            clear=False,
        ), patch("llm_support.is_module_available", side_effect=lambda name: name == "langchain_openai"), patch.dict(
            sys.modules,
            {"langchain_openai": fake_module},
        ):
            output, record = llm_support.run_agent(
                role="test",
                name="ProviderSwitch",
                system_prompt="You are a tester.",
                prompt="Say ok",
                provider_name="alternate",
            )

        self.assertEqual(output, "ok")
        self.assertTrue(record.success)
        self.assertEqual(record.model, "qwen-max")
        self.assertEqual(record.provider, "openai_compatible")
        self.assertEqual(FakeChatOpenAI.last_kwargs["model"], "qwen-max")


if __name__ == "__main__":
    unittest.main()
