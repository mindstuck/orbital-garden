# Known issues and backlog

Priorities: **P0** blocks publishing, **P1** affects the current voice path,
**P2** next milestone, **P3** polish. Update status rather than deleting rows.

| ID | Area | Priority | Status | Description | Follow-up |
| --- | --- | --- | --- | --- | --- |
| SEC-1 | Security | P0 | open | A private key and certificate (`py-server/192.168.100.4-key.pem`, `192.168.100.4.pem`) were committed in `e265d07` and removed in `0db51ba`, but remain in git history on all branches. | Rotate the certificate/key, then rewrite history (e.g. `git filter-repo`) before making the repo public. Do not rely on `.gitignore`. |
| SEC-2 | Security | P1 | open | `.env` exists locally with `POSTGRES_PASSWORD` and unused tokens; it is gitignored. | Keep ignored; never commit. Consider rotating if it was ever pushed. |
| AUTH-1 | Security | P1 | open | The WebSocket origin check is an access check, not authentication. Any same-host client can connect. | Add an explicit token/shared secret or bind to loopback if threat model changes. |
| PERS-1 | Storage | P2 | open | `STORE_BACKEND=postgres` is not implemented; only `none` and `memory` work. | Implement the Postgres store against `store/migrations/0001_init.sql` and an integration test. |
| PERS-2 | Storage | P2 | open | Transcript persistence is opt-in and not implemented for any backend. | Decide retention and implement together with PERS-1. |
| TOOL-1 | Tools | P2 | open | Only the read-only `current_time` tool exists and it is not wired into the chat loop. | Add a tool-calling loop with schema validation and confirmation for writes. |
| WAKE-1 | Voice | P3 | open | Wake word is not implemented; only push-to-talk. | Implement per [ADR 0003](../docs/decisions/0003-wake-word-and-activation.md). |
| CODING-1 | Capability | P3 | open | Coding-agent workspace/command access is not implemented. | Define and review the boundary per ADR 0004 before registering handlers. |
| LLM-1 | Config | P2 | open | The model filename is hardcoded in the `llama-server` command. | Parameterize the path/model and document switching to the coding model. |
| DEP-1 | Reproducibility | P2 | open | Images are pinned by tag, not digest; base OS tags move. | Pin digests and refresh deliberately. |
| TEST-1 | Verification | P2 | open | No automated end-to-end/GPU test on target hardware. | Add an opt-in smoke test and document hardware assumptions. |
| NET-1 | Ops | P2 | open | `LLM_API_URL`/model ports are internal-only; no healthchecks are defined. | Add Compose healthchecks and a startup readiness gate. |
