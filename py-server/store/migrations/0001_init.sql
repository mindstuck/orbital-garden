-- 0001_init: conversations and messages.
--
-- Applied by an operator (or a future migration runner) against the optional
-- PostgreSQL service. No code path consumes these tables yet; see
-- docs/decisions/0002-storage-and-memory.md.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id         text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              text PRIMARY KEY,
    conversation_id text NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role            text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         text NOT NULL,
    seq             bigint GENERATED ALWAYS AS IDENTITY,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_conversation_seq_idx
    ON messages (conversation_id, seq);

INSERT INTO schema_migrations (version)
VALUES ('0001_init')
ON CONFLICT (version) DO NOTHING;
