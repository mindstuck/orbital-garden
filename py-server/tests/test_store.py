"""Conversation store tests."""

import pytest

from config import ConfigError
from store import build_store
from store.memory import InMemoryConversationStore


def test_build_store_none_is_stateless():
    assert build_store("none") is None


def test_build_store_memory():
    assert isinstance(build_store("memory"), InMemoryConversationStore)


def test_build_store_postgres_is_explicitly_unimplemented():
    with pytest.raises(ConfigError, match="not implemented"):
        build_store("postgres")


def test_build_store_rejects_unknown_backend():
    with pytest.raises(ConfigError):
        build_store("sqlite")


def test_history_is_bounded_and_oldest_first():
    store = InMemoryConversationStore(max_messages_per_conversation=3)
    for text in ["one", "two", "three", "four"]:
        store.append("c1", "user", text)
    assert [m.content for m in store.history("c1", 10)] == ["two", "three", "four"]
    assert [m.content for m in store.history("c1", 2)] == ["three", "four"]


def test_delete_removes_conversation():
    store = InMemoryConversationStore()
    store.append("c1", "user", "hi")
    store.delete("c1")
    assert store.history("c1", 10) == []


def test_message_identifiers_are_unique():
    store = InMemoryConversationStore()
    first = store.append("c1", "user", "a")
    second = store.append("c1", "user", "b")
    assert first.id != second.id
    assert first.created_at <= second.created_at
