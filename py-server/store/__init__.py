"""Conversation store selection.

`none` keeps the server stateless (default). `memory` enables ephemeral
short-term history. `postgres` is planned for the persistence milestone; it is
not implemented yet and is rejected loudly rather than silently ignored.
"""

from __future__ import annotations

from config import ConfigError

from .base import ConversationStore, Message
from .memory import InMemoryConversationStore

__all__ = ["ConversationStore", "Message", "build_store"]


def build_store(backend: str) -> ConversationStore | None:
    if backend == "none":
        return None
    if backend == "memory":
        return InMemoryConversationStore()
    if backend == "postgres":
        raise ConfigError(
            "STORE_BACKEND=postgres is planned but not implemented yet. "
            "Use 'memory' for ephemeral history or 'none' for stateless."
        )
    raise ConfigError(f"Unknown STORE_BACKEND: {backend!r}.")
