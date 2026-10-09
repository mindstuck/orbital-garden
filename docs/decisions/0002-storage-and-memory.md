# ADR 0002: Storage and memory ownership

- Status: accepted
- Date: 2026-10-09

## Context

PostgreSQL/pgvector was deployed but unused, `DATABASE_URL` was passed to
`py-server` without being read, and there was no explicit model for
conversation identity, ordering, retention or where transcripts live.

## Decision

- **Persistence is opt-in.** `STORE_BACKEND` defaults to `none` (stateless).
  `memory` enables ephemeral short-term history for prompt context and is
  lost on restart. PostgreSQL remains provisioned behind the Compose `db`
  profile and is not started by default.
- **Ownership model** (mirrored by `store/base.py` and `0001_init.sql`):
  - `conversation_id`: opaque string, one per client session by default.
  - `message.id`: unique identifier (UUID in memory, text/UUID in SQL).
  - Ordering: `messages.seq` (monotonic) with `created_at` for display.
  - Retention/deletion: `ConversationStore.delete(conversation_id)` removes a
    conversation and cascades to its messages.
- **Transcripts are stored intentionally.** The in-memory store is ephemeral;
  any persistent backend must be explicitly enabled and documented. Raw
  transcript text is never logged.
- **Migrations are append-only** and versioned in `schema_migrations`
  (`py-server/store/migrations/`).
- **Long-term knowledge accumulation and vector retrieval are deferred.**
  pgvector being installed is not a reason to use it.

## Consequences

- The default deployment is stateless and writes no conversation data.
- Enabling memory is a one-line configuration change; enabling PostgreSQL
  requires a store implementation plus running migrations.
- DB state lives on the `db_data` named volume with documented backup and
  restore (`store/migrations/README.md`), not a repository path.
