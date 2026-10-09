# ai-stack

A single-user, LAN-oriented local AI stack: a browser voice/text client talking
to a Python pipeline that runs speech-to-text, a local LLM and text-to-speech,
with a local `llama.cpp` model server.

> Status: work in progress. The voice pipeline is implemented and runnable.
> Memory, tools, wake word, a coding agent and additional clients are planned;
> they are documented but not operational. See [docs/issues.md](docs/issues.md).

## What actually runs

| Component | State | Notes |
| --- | --- | --- |
| `py-server` | implemented | FastAPI + WebSocket edge, turn coordinator, STT/LLM/TTS providers |
| `llama-server` | implemented | `llama.cpp` serving `L3-8B-Stheno-v3.2-Q4_K_M.gguf` |
| `db` (PostgreSQL/pgvector) | optional | behind the `db` Compose profile; no code uses it yet |
| Memory / conversation store | interface only | in-memory short-term history available via `STORE_BACKEND=memory` |
| Tools | interface only | registry + read-only `current_time`; not wired into chat |
| Wake word | planned | see [ADR 0003](docs/decisions/0003-wake-word-and-activation.md) |
| Coding agent | planned | see [ADR 0004](docs/decisions/0004-coding-agent-boundary.md) |
| 9router / Ollama / other clients | examples | see [docs/examples/compose-services.md](docs/examples/compose-services.md) |

## Architecture and data flow

```
Browser (mic / text)
   │  ws://<host>:8400/ws  (JSON control + binary audio)
   ▼
py-server ── api/server.py        transport, origin check, concurrency, error frames
   │        pipeline/coordinator   turn orchestration (persona + history)
   │        providers/*            WhisperSTT · LlamaCppLLM · PiperTTS
   │
   ├─► stt  → text
   ├─► llm  → http://llama-server:8000/v1  (internal HTTP only)
   └─► tts  → ordered WAV chunks ──► Browser playback queue
```

**Trust boundaries**

- Only `py-server` publishes a host port. `llama-server` and `db` are reachable
  on the Compose network only.
- The `/ws` endpoint checks the request `Origin` against the same host (or
  `ALLOWED_ORIGINS`). This is an access check, not authentication.
- Internal service traffic is plain HTTP. Client-facing TLS is opt-in; see
  [ADR 0001](docs/decisions/0001-network-and-tls.md).

## Prerequisites

- Docker Engine with Compose v2.
- NVIDIA GPU, a compatible driver and the NVIDIA Container Toolkit. Both
  `llama-server` and `py-server` request a GPU.
- Enough VRAM for the configured model (`-ngl 24 -c 8192`; tune in
  `compose.yaml` for your card).
- Runtime assets, **not committed**:
  - GGUF model at `models/L3-8B-Stheno-v3.2-Q4_K_M.gguf` (matching the
    `compose.yaml` command).
  - Piper voice at `py-server/voices/hal.onnx` and `hal.onnx.json`
    (see [py-server/voices/README.md](py-server/voices/README.md)).
  - CUDA libraries for faster-whisper at `py-server/cuda_libs/` when running
    STT on GPU.

## Setup

1. Create configuration from the sanitized example:

   ```sh
   cp .env.example .env
   ```

   `POSTGRES_PASSWORD` is only required if you enable the `db` profile. All
   other variables have safe defaults.

2. Provision the model, voice and CUDA assets listed above.

3. Build and start:

   ```sh
   docker compose up -d --build
   ```

   Optionally start the database for the future persistence milestone:

   ```sh
   docker compose --profile db up -d
   ```

4. Open `http://<host>:8400/` and use the text box or "Press to Talk".

5. Stop:

   ```sh
   docker compose down
   ```

## Configuration

Set these in `.env` (see `.env.example` for the full list):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PY_SERVER_BIND` / `PY_SERVER_PORT` | `0.0.0.0` / `8400` | Published client endpoint |
| `ALLOWED_ORIGINS` | empty (same host) | Allowed browser origins |
| `LLM_API_URL` | `http://llama-server:8000/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `stheno` | Model name sent to the server |
| `PERSONA` | `assistant` | `assistant`, `character` or `coding` |
| `SYSTEM_PROMPT` | unset | Overrides the persona prompt |
| `STT_MODEL` / `STT_DEVICE` | `base` / `cuda` | faster-whisper settings |
| `TTS_VOICE_PATH` | `./voices/hal.onnx` | Piper voice |
| `STORE_BACKEND` | `none` | `none` or `memory` (ephemeral history) |
| `SSL_CERTFILE` / `SSL_KEYFILE` | unset | Opt-in client-facing TLS |

## TLS

By default `py-server` serves plain HTTP and the browser derives `ws://` or
`wss://` from the page protocol. To enable TLS directly, set both
`SSL_CERTFILE` and `SSL_KEYFILE` and mount the files read-only. A reverse proxy
may terminate TLS instead. Certificates are never baked into images.

## What is stored locally

- `models/`, `py-server/voices/`, `py-server/cuda_libs/` — runtime assets,
  gitignored.
- `huggingface_cache` named volume — faster-whisper model download cache.
- `db_data` named volume — PostgreSQL data, only with the `db` profile. Back up
  with `pg_dump` (see [store/migrations/README.md](py-server/store/migrations/README.md)).
- Conversations — **not persisted by default**. `STORE_BACKEND=memory` keeps
  bounded short-term history in RAM; raw transcripts are never logged.

## Development and verification

```sh
cd py-server
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
ruff format . && ruff check . && mypy . && python -m pytest
```

Unit tests (chunking, config, protocol, coordinator with fakes) do **not**
require a GPU. End-to-end checks require the real services on the target
hardware. Validate Compose with `docker compose config`.

## Troubleshooting

- **`Piper voice not found`** — place `hal.onnx` and `hal.onnx.json` in
  `py-server/voices/` or set `TTS_VOICE_PATH`.
- **LLM requests fail / connection refused** — ensure `llama-server` is up and
  `LLM_API_URL` points at it; the model must exist at the path in
  `compose.yaml`.
- **GPU not available in a container** — install the NVIDIA Container Toolkit
  and confirm `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`.
- **Browser says "Connection error" or "Disconnected"** — check the origin and
  that you are loading the page over the same scheme/host as `/ws`.

## Documentation

- [docs/decisions/](docs/decisions/) — architecture decision records.
- [docs/issues.md](docs/issues.md) — known limitations and follow-ups.
- [docs/examples/compose-services.md](docs/examples/compose-services.md) —
  non-active Compose examples.
