"""OpenAI-compatible llama.cpp chat adapter.

Provider-specific sampling parameters live here, not in the coordinator.
"""
from __future__ import annotations

import logging
from typing import Iterator

from openai import OpenAI

from .base import ChatMessage

logger = logging.getLogger(__name__)


class LlamaCppLLM:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "not-needed",
        timeout: float = 120.0,
        temperature: float = 0.9,
        top_p: float = 1.0,
        frequency_penalty: float = 0.1,
        max_tokens: int = 400,
        extra_body: dict | None = None,
    ) -> None:
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self._sampling = {
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "max_tokens": max_tokens,
        }
        self._extra_body = extra_body or {}

    def stream_chat(self, messages: list[ChatMessage]) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            extra_body=self._extra_body,
            **self._sampling,
        )
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yield content
