"""Composition root for py-server.

Wires validated settings, provider adapters and the turn coordinator into the
FastAPI/WebSocket edge. Uvicorn imports this module as ``main:app``.
"""
from __future__ import annotations

import logging

from api.server import create_app
from config import Settings
from personas import resolve_system_prompt
from pipeline.coordinator import AssistantCoordinator
from providers.llama_llm import LlamaCppLLM
from providers.piper_tts import PiperTTS
from providers.whisper_stt import WhisperSTT
from store import build_store
from tools import build_default_registry

logging.basicConfig(level=logging.INFO)

settings = Settings.from_env()

coordinator = AssistantCoordinator(
    stt=WhisperSTT(
        model_name=settings.stt_model,
        device=settings.stt_device,
        compute_type=settings.stt_compute_type,
        language=settings.stt_language,
        beam_size=settings.stt_beam_size,
    ),
    llm=LlamaCppLLM(
        base_url=settings.llm_api_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout,
        temperature=settings.llm_temperature,
        top_p=settings.llm_top_p,
        frequency_penalty=settings.llm_frequency_penalty,
        max_tokens=settings.llm_max_tokens,
        extra_body=settings.llm_extra_body(),
    ),
    tts=PiperTTS(settings.tts_voice_path),
    system_prompt=resolve_system_prompt(settings.persona, settings.system_prompt),
    store=build_store(settings.store_backend),
    history_max_messages=settings.history_max_messages,
)

app = create_app(settings, coordinator, tools=build_default_registry())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
