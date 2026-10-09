"""Provider-neutral interfaces for the assistant pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Typed transcription outcome. `text` is None on failure."""

    text: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.text is not None


@dataclass(frozen=True)
class SynthesisResult:
    """Typed synthesis outcome. `audio` is None on failure."""

    audio: bytes | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.audio is not None


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, suffix: str = ".webm") -> TranscriptionResult: ...


class LLMProvider(Protocol):
    def stream_chat(self, messages: list[ChatMessage]) -> Iterator[str]: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str) -> SynthesisResult: ...
