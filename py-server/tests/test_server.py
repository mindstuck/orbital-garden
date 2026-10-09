"""End-to-end WebSocket edge tests with fake providers (no GPU required)."""

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.server import create_app
from config import Settings
from pipeline.coordinator import AssistantCoordinator
from providers.base import SynthesisResult, TranscriptionResult


class FakeSTT:
    def transcribe(self, audio, suffix=".webm"):
        return TranscriptionResult(text="transcribed words")


class FakeLLM:
    def stream_chat(self, messages):
        yield "Hello there. "
        yield "General Kenobi."


class FakeTTS:
    def synthesize(self, text):
        return SynthesisResult(audio=("AUDIO:" + text).encode())


def build_client(**env):
    settings = Settings.from_env(env)
    coordinator = AssistantCoordinator(
        stt=FakeSTT(), llm=FakeLLM(), tts=FakeTTS(), system_prompt="SYS"
    )
    return TestClient(create_app(settings, coordinator))


def drain_until_idle(ws):
    while True:
        message = ws.receive()
        if message.get("text"):
            payload = json.loads(message["text"])
            if payload.get("type") == "status" and payload.get("state") == "idle":
                return


def test_index_and_static_assets_are_served():
    client = build_client()
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_text_turn_streams_status_audio_and_idle():
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "text", "turn_id": "t1", "text": "hi"}))
        assert json.loads(ws.receive_text())["state"] == "thinking"
        assert json.loads(ws.receive_text())["state"] == "speaking"
        assert ws.receive_bytes() == b"AUDIO:Hello there."
        assert ws.receive_bytes() == b"AUDIO:General Kenobi."
        assert json.loads(ws.receive_text())["state"] == "idle"


def test_malformed_message_returns_typed_error():
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        error = json.loads(ws.receive_text())
        assert error["type"] == "error" and error["code"] == "bad_json"


def test_binary_without_audio_start_is_rejected():
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_bytes(b"123")
        error = json.loads(ws.receive_text())
        assert error["code"] == "no_audio_turn"


def test_audio_turn_transcribes_and_replies():
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "audio_start", "turn_id": "a1", "mime": "audio/webm"}))
        assert json.loads(ws.receive_text())["state"] == "recording"
        ws.send_bytes(b"fake-audio")
        ws.send_text(json.dumps({"type": "audio_end", "turn_id": "a1"}))
        assert json.loads(ws.receive_text())["state"] == "transcribing"
        transcript = json.loads(ws.receive_text())
        assert transcript["type"] == "transcript" and transcript["text"] == "transcribed words"
        drain_until_idle(ws)


def test_disconnect_mid_turn_is_handled():
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "text", "turn_id": "t1", "text": "hi"}))
        ws.receive_text()  # thinking
    # Reconnecting after an abrupt close must still work.
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "text", "turn_id": "t2", "text": "again"}))
        assert json.loads(ws.receive_text())["state"] == "thinking"


def test_disallowed_origin_is_rejected():
    client = build_client(ALLOWED_ORIGINS="http://good.example")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={"origin": "http://evil.example"}) as ws:
            ws.receive_text()


def test_turns_do_not_write_scratch_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = build_client()
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "audio_start", "turn_id": "a1", "mime": "audio/webm"}))
        ws.receive_text()
        ws.send_bytes(b"fake-audio")
        ws.send_text(json.dumps({"type": "audio_end", "turn_id": "a1"}))
        drain_until_idle(ws)
    assert list(tmp_path.iterdir()) == []
