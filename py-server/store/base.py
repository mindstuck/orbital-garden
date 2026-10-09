"""Conversation store interfaces and value objects.

Identifiers and ordering are explicit so any backend (in-memory, PostgreSQL)
can satisfy the same contract:

- A conversation is identified by an opaque string (`conversation_id`).
- A message has a unique `id`, belongs to one conversation, carries `role`
  and `content`, and records `created_at` (epoch seconds).
- History is returned oldest-first and bounded by `limit`.
- `delete` removes a conversation and its messages (retention/deletion).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: float


class ConversationStore(Protocol):
    def append(self, conversation_id: str, role: str, content: str) -> Message: ...

    def history(self, conversation_id: str, limit: int) -> list[Message]: ...

    def delete(self, conversation_id: str) -> None: ...
