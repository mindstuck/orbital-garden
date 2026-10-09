"""WebSocket message contract for py-server.

This module is intentionally dependency-free so the contract can be unit
tested without loading fastapi, torch or the model servers.

Client -> server
----------------
Text frames carry JSON:

    {"type": "text", "turn_id": "abc", "text": "hello"}
    {"type": "audio_start", "turn_id": "abc", "mime": "audio/webm"}
    {"type": "audio_end", "turn_id": "abc"}

Binary frames carry raw audio bytes for the active audio turn. A frame with
no open audio turn is a protocol error.

Server -> client
----------------
Text frames carry JSON:

    {"type": "status", "turn_id": "abc", "state": "thinking"}
    {"type": "transcript", "turn_id": "abc", "text": "hello"}
    {"type": "error", "turn_id": "abc", "code": "bad_message", "message": "..."}

Binary frames carry ordered WAV audio chunks for the current turn.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

# Bounds keep a single client from exhausting memory or GPU time.
MAX_TEXT_CHARS = 8000
MAX_TEXT_FRAME_BYTES = 64_000
MAX_AUDIO_FRAME_BYTES = 1_000_000
MAX_AUDIO_TURN_BYTES = 20_000_000
MAX_AUDIO_MIME_PREFIX = "audio/"


class ProtocolError(Exception):
    """A client message violated the WebSocket contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TextTurn:
    turn_id: str
    text: str


@dataclass(frozen=True)
class AudioStart:
    turn_id: str
    mime: str


@dataclass(frozen=True)
class AudioEnd:
    turn_id: str


def new_turn_id() -> str:
    return uuid.uuid4().hex


def encode_event(event_type: str, **fields: object) -> str:
    """Serialize a server -> client text event."""
    return json.dumps({"type": event_type, **fields})


def parse_text_message(raw: str) -> TextTurn | AudioStart | AudioEnd:
    """Parse and validate a client text frame.

    Raises ProtocolError for malformed or out-of-bounds messages.
    """
    if len(raw.encode("utf-8")) > MAX_TEXT_FRAME_BYTES:
        raise ProtocolError("message_too_large", "Control message exceeds the size limit.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError("bad_json", "Control message is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ProtocolError("bad_message", "Control message must be a JSON object.")

    message_type = payload.get("type")
    turn_id = payload.get("turn_id") or new_turn_id()
    if not isinstance(turn_id, str) or not turn_id:
        raise ProtocolError("bad_message", "turn_id must be a non-empty string.")

    if message_type == "text":
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProtocolError("bad_message", "text turns require non-empty text.")
        if len(text) > MAX_TEXT_CHARS:
            raise ProtocolError("message_too_large", "Text exceeds the character limit.")
        return TextTurn(turn_id=turn_id, text=text)

    if message_type == "audio_start":
        mime = payload.get("mime", "audio/webm")
        if not isinstance(mime, str) or not mime.startswith(MAX_AUDIO_MIME_PREFIX):
            raise ProtocolError("unsupported_media", "Only audio/* media types are accepted.")
        return AudioStart(turn_id=turn_id, mime=mime)

    if message_type == "audio_end":
        return AudioEnd(turn_id=turn_id)

    raise ProtocolError("unknown_type", f"Unknown message type: {message_type!r}.")
