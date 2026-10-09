"""Coordinator/provider-substitution tests using fakes (no GPU required)."""

import pytest

from pipeline.coordinator import AssistantCoordinator, PipelineError
from providers.base import ChatMessage, SynthesisResult, TranscriptionResult
from store.memory import InMemoryConversationStore


class FakeSTT:
    def __init__(self, text="hello there"):
        self.text = text

    def transcribe(self, audio, suffix=".webm"):
        return TranscriptionResult(text=self.text)


class FakeLLM:
    def __init__(self, *deltas):
        self.deltas = deltas or ("First sentence. ", "Second sentence.")
        self.calls = []

    def stream_chat(self, messages):
        self.calls.append(list(messages))
        yield from self.deltas


class FakeTTS:
    def synthesize(self, text):
        return SynthesisResult(audio=("AUDIO:" + text).encode())


class FailingTTS:
    def synthesize(self, text):
        return SynthesisResult(audio=None, error="boom")


def make_coordinator(**kwargs):
    return AssistantCoordinator(
        stt=kwargs.get("stt", FakeSTT()),
        llm=kwargs.get("llm", FakeLLM()),
        tts=kwargs.get("tts", FakeTTS()),
        system_prompt=kwargs.get("system_prompt", "SYS"),
        store=kwargs.get("store"),
        history_max_messages=kwargs.get("history_max_messages", 20),
    )


def test_transcribe_delegates_to_provider():
    result = make_coordinator().transcribe(b"audio")
    assert result.ok and result.text == "hello there"


def test_stream_reply_chunks_and_synthesizes_in_order():
    audio = list(make_coordinator().stream_reply("hi"))
    assert audio == [b"AUDIO:First sentence.", b"AUDIO:Second sentence."]


def test_stream_reply_builds_system_and_user_messages():
    llm = FakeLLM()
    coordinator = make_coordinator(llm=llm, system_prompt="PERSONA")
    list(coordinator.stream_reply("question"))
    assert llm.calls[0] == [ChatMessage("system", "PERSONA"), ChatMessage("user", "question")]


def test_synthesis_failure_raises_pipeline_error():
    coordinator = make_coordinator(tts=FailingTTS())
    with pytest.raises(PipelineError):
        list(coordinator.stream_reply("hi"))


def test_store_supplies_bounded_history_and_records_turn():
    llm = FakeLLM()
    store = InMemoryConversationStore()
    coordinator = make_coordinator(llm=llm, store=store)
    list(coordinator.stream_reply("hello", "conv-1"))
    list(coordinator.stream_reply("again", "conv-1"))
    assert llm.calls[1] == [
        ChatMessage("system", "SYS"),
        ChatMessage("user", "hello"),
        ChatMessage("assistant", "First sentence. Second sentence."),
        ChatMessage("user", "again"),
    ]
    assert [m.content for m in store.history("conv-1", 10)] == [
        "hello",
        "First sentence. Second sentence.",
        "again",
        "First sentence. Second sentence.",
    ]


def test_stateless_when_no_store():
    coordinator = make_coordinator()
    assert list(coordinator.stream_reply("x", "ignored")) == [
        b"AUDIO:First sentence.",
        b"AUDIO:Second sentence.",
    ]
