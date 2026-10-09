# ADR 0004: Coding-agent and tool capability boundary

- Status: proposed
- Date: 2026-10-09

## Context

Tools and a coding agent will need filesystem and command access. That is a
higher-risk capability than chat generation and must not be entangled with
generated text or conversation memory.

## Decision

- Tool execution is separate from generated text and memory. `tools/registry.py`
  defines explicit `input_schema`/`output_schema`, a per-tool timeout and a
  `read_only` flag. The first tool is the read-only `current_time`.
- Handlers run off the event loop with a timeout; unknown tools and invalid
  arguments return a typed `ToolResult` error rather than raising into chat.
- The coding agent is a **separate capability boundary**, enabled only when a
  workspace root is configured:
  - All file paths are resolved and constrained to an explicit workspace
    directory; traversal outside it is rejected.
  - Commands run from an explicit working directory with an allowlist, a
    timeout and captured output. Writes require explicit confirmation.
  - Network access is denied by default.
- Generated text never implies tool execution; a tool runs only from an
  explicit, schema-validated call.
- Router/Telegram/desktop/mobile/web integrations stay behind the transport
  and LLM adapter contracts until implemented; they are not presented as
  running services.

## Consequences

- The first tool carries no filesystem or command risk.
- Adding a coding agent requires defining and reviewing its boundary before
  any handler is registered.
- The registry can be tested without GPU or network access.
