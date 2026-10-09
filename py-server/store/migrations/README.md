# Store migrations

SQL migrations for the optional PostgreSQL-backed conversation store.

The active code does **not** use PostgreSQL yet. `STORE_BACKEND` defaults to
`none`; `memory` provides ephemeral short-term history. PostgreSQL remains a
provisioned-but-optional service until the persistence milestone lands (see
`docs/decisions/0002-storage-and-memory.md`).

## Workflow

1. Start the optional database: `docker compose --profile db up -d db`.
2. Apply migrations in order with `psql`:

   ```sh
   for f in py-server/store/migrations/*.sql; do
     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
   done
   ```

3. Each file records its version in `schema_migrations`; keep files
   append-only once applied.

## Backup and restore

- Backup: `docker compose --profile db exec -T db pg_dump -U ai ai > backup.sql`
- Restore: `docker compose --profile db exec -T db psql -U ai ai < backup.sql`

Store backups outside the repository.
