"""Ephemeral in-memory conversation store (short-term history).

Nothing is written to disk, so this is safe by default. Memory is bounded per
conversation to avoid unbounded growth in a long-running process.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque

from .base import ConversationStore, Message


class InMemoryConversationStore(ConversationStore):
    def __init__(self, max_messages_per_conversation: int = 200) -> None:
        self._max = max_messages_per_conversation
        self._data: dict[str, deque[Message]] = defaultdict(lambda: deque(maxlen=self._max))
        self._lock = threading.Lock()

    def append(self, conversation_id: str, role: str, content: str) -> Message:
        message = Message(
            id=uuid.uuid4().hex,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=time.time(),
        )
        with self._lock:
            self._data[conversation_id].append(message)
        return message

    def history(self, conversation_id: str, limit: int) -> list[Message]:
        with self._lock:
            items = list(self._data.get(conversation_id, ()))
        if limit and limit > 0:
            items = items[-limit:]
        return items

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            self._data.pop(conversation_id, None)
