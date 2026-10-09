"""WebSocket wire-contract tests (no GPU or network required)."""

import json

import pytest

from api.protocol import (
    AudioEnd,
    AudioStart,
    ProtocolError,
    TextTurn,
    encode_event,
    parse_text_message,
)


def test_parses_text_turn():
    event = parse_text_message('{"type": "text", "turn_id": "t1", "text": "hello"}')
    assert event == TextTurn(turn_id="t1", text="hello")


def test_parses_audio_start_and_end():
    started = parse_text_message('{"type": "audio_start", "turn_id": "t2", "mime": "audio/webm"}')
    assert started == AudioStart(turn_id="t2", mime="audio/webm")
    ended = parse_text_message('{"type": "audio_end", "turn_id": "t2"}')
    assert ended == AudioEnd(turn_id="t2")


def test_turn_id_is_generated_when_missing():
    event = parse_text_message('{"type": "text", "text": "hi"}')
    assert isinstance(event, TextTurn) and event.turn_id


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("not json", "bad_json"),
        ("[]", "bad_message"),
        ('{"type": "nope"}', "unknown_type"),
        ('{"type": "text", "text": ""}', "bad_message"),
        ('{"type": "audio_start", "mime": "text/plain"}', "unsupported_media"),
    ],
)
def test_rejects_bad_messages(raw, code):
    with pytest.raises(ProtocolError) as exc_info:
        parse_text_message(raw)
    assert exc_info.value.code == code


def test_rejects_oversized_text():
    raw = json.dumps({"type": "text", "text": "x" * 9000})
    with pytest.raises(ProtocolError) as exc_info:
        parse_text_message(raw)
    assert exc_info.value.code == "message_too_large"


def test_encode_event_round_trips():
    payload = json.loads(encode_event("status", turn_id="t1", state="thinking"))
    assert payload == {"type": "status", "turn_id": "t1", "state": "thinking"}
