"""Assistant turn orchestration.

The coordinator wires narrow provider interfaces together and knows nothing
about HTTP, WebSockets, concurrency or wire formats. Transport concerns stay
in :mod:`api.server`.
"""
from __future__ import annotations

from typing import Iterator

from providers.base import ChatMessage, LLMProvider, STTProvider, TTSProvider, TranscriptionResult
from store.base import ROLE_ASSISTANT, ROLE_USER, ConversationStore

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
        store: ConversationStore | None = None,
        history_max_messages: int = 20,
    ) -> None:
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._system_prompt = system_prompt
        self._store = store
        self._history_max_messages = history_max_messages

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> TranscriptionResult:
        return self._stt.transcribe(audio, suffix)

    def stream_reply(self, user_text: str, conversation_id: str | None = None) -> Iterator[bytes]:
        """Yield ordered WAV audio chunks for a single user turn.

        When a store and ``conversation_id`` are provided, bounded short-term
        history is used for prompt context and the turn is recorded.
        """
        history = []
        if self._store is not None and conversation_id:
            history = self._store.history(conversation_id, self._history_max_messages)
            self._store.append(conversation_id, ROLE_USER, user_text)

        messages = [ChatMessage(role="system", content=self._system_prompt)]
        messages += [ChatMessage(role=m.role, content=m.content) for m in history]
        messages.append(ChatMessage(role="user", content=user_text))

        reply_parts: list[str] = []
        for spoken in chunk_text(self._llm.stream_chat(messages)):
            result = self._tts.synthesize(spoken)
            if not result.ok:
                raise PipelineError(result.error or "speech synthesis failed")
            reply_parts.append(spoken)
            yield result.audio

        if self._store is not None and conversation_id:
            self._store.append(conversation_id, ROLE_ASSISTANT, " ".join(reply_parts))
