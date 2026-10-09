"""Centralized, validated runtime settings for py-server.

Configuration comes from the environment (Compose `environment`/`env_file`
or a local `.env` loaded by the entrypoint). Nothing here imports fastapi,
torch or the model servers, so it stays cheap to import and easy to test.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when the environment contains invalid configuration."""


def _env(env: dict[str, str], name: str, default: str) -> str:
    value = env.get(name)
    return default if value is None or value == "" else value


def _env_int(env: dict[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}.") from exc


def _env_float(env: dict[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}.") from exc


def _env_csv(env: dict[str, str], name: str) -> tuple[str, ...]:
    raw = env.get(name, "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _env_bool(env: dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Client-facing WebSocket / HTTP server.
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: tuple[str, ...] = ()
    max_gpu_concurrency: int = 1

    # LLM (OpenAI-compatible llama.cpp endpoint).
    llm_api_url: str = "http://llama-server:8000/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "stheno"
    llm_timeout: float = 120.0
    llm_temperature: float = 0.9
    llm_top_p: float = 1.0
    llm_frequency_penalty: float = 0.1
    llm_max_tokens: int = 400
    llm_min_p: float = 0.05
    llm_top_k: int = 0
    llm_repeat_penalty: float = 1.05
    llm_dry_multiplier: float = 0.8
    llm_dry_base: float = 1.75
    llm_dry_allowed_length: int = 2

    # Speech-to-text.
    stt_model: str = "base"
    stt_device: str = "cuda"
    stt_compute_type: str = "float16"
    stt_language: str = "en"
    stt_beam_size: int = 5

    # Text-to-speech.
    tts_voice_path: str = "./voices/hal.onnx"

    # Assistant behaviour. `system_prompt` overrides the selected persona.
    system_prompt: str | None = None
    persona: str = "assistant"

    # Conversation storage (opt-in).
    store_backend: str = "none"
    history_max_messages: int = 20
    database_url: str = ""
    transcript_persistence: bool = False

    def llm_extra_body(self) -> dict[str, float | int]:
        """Provider-specific sampling parameters kept out of the coordinator."""
        return {
            "min_p": self.llm_min_p,
            "top_k": self.llm_top_k,
            "repeat_penalty": self.llm_repeat_penalty,
            "dry_multiplier": self.llm_dry_multiplier,
            "dry_base": self.llm_dry_base,
            "dry_allowed_length": self.llm_dry_allowed_length,
        }

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        source = dict(os.environ if env is None else env)
        settings = cls(
            host=_env(source, "HOST", "0.0.0.0"),
            port=_env_int(source, "PORT", 8000),
            allowed_origins=_env_csv(source, "ALLOWED_ORIGINS"),
            max_gpu_concurrency=_env_int(source, "MAX_GPU_CONCURRENCY", 1),
            llm_api_url=_env(source, "LLM_API_URL", "http://llama-server:8000/v1"),
            llm_api_key=_env(source, "LLM_API_KEY", "not-needed"),
            llm_model=_env(source, "LLM_MODEL", "stheno"),
            llm_timeout=_env_float(source, "LLM_TIMEOUT", 120.0),
            llm_temperature=_env_float(source, "LLM_TEMPERATURE", 0.9),
            llm_top_p=_env_float(source, "LLM_TOP_P", 1.0),
            llm_frequency_penalty=_env_float(source, "LLM_FREQUENCY_PENALTY", 0.1),
            llm_max_tokens=_env_int(source, "LLM_MAX_TOKENS", 400),
            llm_min_p=_env_float(source, "LLM_MIN_P", 0.05),
            llm_top_k=_env_int(source, "LLM_TOP_K", 0),
            llm_repeat_penalty=_env_float(source, "LLM_REPEAT_PENALTY", 1.05),
            llm_dry_multiplier=_env_float(source, "LLM_DRY_MULTIPLIER", 0.8),
            llm_dry_base=_env_float(source, "LLM_DRY_BASE", 1.75),
            llm_dry_allowed_length=_env_int(source, "LLM_DRY_ALLOWED_LENGTH", 2),
            stt_model=_env(source, "STT_MODEL", "base"),
            stt_device=_env(source, "STT_DEVICE", "cuda"),
            stt_compute_type=_env(source, "STT_COMPUTE_TYPE", "float16"),
            stt_language=_env(source, "STT_LANGUAGE", "en"),
            stt_beam_size=_env_int(source, "STT_BEAM_SIZE", 5),
            tts_voice_path=_env(source, "TTS_VOICE_PATH", "./voices/hal.onnx"),
            system_prompt=_env(source, "SYSTEM_PROMPT", "") or None,
            persona=_env(source, "PERSONA", "assistant"),
            store_backend=_env(source, "STORE_BACKEND", "none"),
            history_max_messages=_env_int(source, "HISTORY_MAX_MESSAGES", 20),
            database_url=_env(source, "DATABASE_URL", ""),
            transcript_persistence=_env_bool(source, "TRANSCRIPT_PERSISTENCE", False),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        errors: list[str] = []
        if self.max_gpu_concurrency < 1:
            errors.append("MAX_GPU_CONCURRENCY must be at least 1.")
        if not 0.0 <= self.llm_temperature <= 2.0:
            errors.append("LLM_TEMPERATURE must be between 0 and 2.")
        if not 0.0 < self.llm_top_p <= 1.0:
            errors.append("LLM_TOP_P must be in (0, 1].")
        if not -2.0 <= self.llm_frequency_penalty <= 2.0:
            errors.append("LLM_FREQUENCY_PENALTY must be between -2 and 2.")
        if self.llm_max_tokens <= 0:
            errors.append("LLM_MAX_TOKENS must be positive.")
        if self.llm_timeout <= 0:
            errors.append("LLM_TIMEOUT must be positive.")
        if self.stt_beam_size < 1:
            errors.append("STT_BEAM_SIZE must be at least 1.")
        if not 1 <= self.port <= 65535:
            errors.append("PORT must be a valid TCP port.")
        if self.store_backend not in {"none", "memory", "postgres"}:
            errors.append("STORE_BACKEND must be one of: none, memory, postgres.")
        if self.history_max_messages < 0:
            errors.append("HISTORY_MAX_MESSAGES must not be negative.")
        if errors:
            raise ConfigError("Invalid configuration:\n- " + "\n- ".join(errors))
