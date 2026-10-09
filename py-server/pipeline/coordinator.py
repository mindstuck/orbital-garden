"""Assistant turn orchestration.

The coordinator wires narrow provider interfaces together and knows nothing
about HTTP, WebSockets, concurrency or wire formats. Transport concerns stay
in :mod:`api.server`.
"""
from __future__ import annotations

from typing import Iterator

from providers.base import ChatMessage, LLMProvider, STTProvider, TTSProvider, TranscriptionResult

from .chunking import chunk_text


class PipelineError(RuntimeError):
    """A provider failed while producing a turn."""


class AssistantCoordinator:
    def __init__(
        self,
        *,
        stt: STTProvider,
        llm: LLMProvider,
        tts: TTSProvider,
        system_prompt: str,
    ) -> None:
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._system_prompt = system_prompt

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> TranscriptionResult:
        return self._stt.transcribe(audio, suffix)

    def stream_reply(self, user_text: str) -> Iterator[bytes]:
        """Yield ordered WAV audio chunks for a single user turn."""
        messages = [
            ChatMessage(role="system", content=self._system_prompt),
            ChatMessage(role="user", content=user_text),
        ]
        for spoken in chunk_text(self._llm.stream_chat(messages)):
            result = self._tts.synthesize(spoken)
            if not result.ok:
                raise PipelineError(result.error or "speech synthesis failed")
            yield result.audio
