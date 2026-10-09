# ADR 0001: Container network and TLS boundary

- Status: accepted
- Date: 2026-10-09

## Context

The stack runs on a single LAN host and serves one user. Previously the
browser HTML always opened `wss://`, the `py-server` image baked a
machine-specific LAN certificate, `llm.py` ignored `LLM_API_URL` and called
`host.docker.internal:8300`, and the database and model servers published
ports on the LAN.

## Decision

- Internal service-to-service traffic uses **plain HTTP** over the Compose
  network and service DNS names (`http://llama-server:8000/v1`). Those
  services are not published to the host.
- Only the user-facing `py-server` endpoint is published, on
  `PY_SERVER_BIND:PY_SERVER_PORT` (defaults `0.0.0.0:8400`).
- `py-server` serves plain HTTP by default and derives `ws://` vs `wss://`
  in the browser from `window.location.protocol`, so no scheme is assumed.
- TLS is **opt-in** at the `py-server` container: set both `SSL_CERTFILE`
  and `SSL_KEYFILE` and mount the certificate material read-only. The image
  never contains certificates.
- A reverse proxy may terminate TLS instead; in that case leave
  `SSL_CERTFILE`/`SSL_KEYFILE` unset and forward to `py-server:8000`.

## Consequences

- No LAN IP, Docker Desktop host alias, or host-specific certificate is
  required for a working deployment.
- The access boundary is the `py-server` port; the database and model
  servers are reachable only inside the Compose network.
- Enabling client-facing TLS is an explicit operator action.
