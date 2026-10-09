"""Configuration validation tests (no GPU or network required)."""

import pytest

from config import ConfigError, Settings


def test_defaults_are_safe():
    settings = Settings.from_env({})
    assert settings.llm_api_url == "http://llama-server:8000/v1"
    assert settings.store_backend == "none"
    assert settings.persona == "assistant"
    assert settings.system_prompt is None
    assert settings.max_gpu_concurrency == 1
    assert settings.allowed_origins == ()


def test_environment_overrides_are_parsed():
    settings = Settings.from_env(
        {
            "LLM_TEMPERATURE": "0.5",
            "LLM_MODEL": "qwen",
            "MAX_GPU_CONCURRENCY": "2",
            "ALLOWED_ORIGINS": "http://a , http://b",
            "SYSTEM_PROMPT": "Be brief.",
            "STORE_BACKEND": "memory",
        }
    )
    assert settings.llm_temperature == 0.5
    assert settings.llm_model == "qwen"
    assert settings.max_gpu_concurrency == 2
    assert settings.allowed_origins == ("http://a", "http://b")
    assert settings.system_prompt == "Be brief."
    assert settings.store_backend == "memory"


@pytest.mark.parametrize(
    "env",
    [
        {"LLM_TEMPERATURE": "hot"},
        {"LLM_TEMPERATURE": "5"},
        {"LLM_TOP_P": "0"},
        {"MAX_GPU_CONCURRENCY": "0"},
        {"LLM_MAX_TOKENS": "0"},
        {"STT_BEAM_SIZE": "0"},
        {"STORE_BACKEND": "bogus"},
        {"HISTORY_MAX_MESSAGES": "-1"},
        {"PORT": "70000"},
    ],
)
def test_invalid_configuration_is_rejected(env):
    with pytest.raises(ConfigError):
        Settings.from_env(env)


def test_extra_body_holds_provider_sampling():
    settings = Settings.from_env({"LLM_MIN_P": "0.1", "LLM_TOP_K": "40"})
    body = settings.llm_extra_body()
    assert body["min_p"] == 0.1
    assert body["top_k"] == 40
    assert "dry_multiplier" in body
