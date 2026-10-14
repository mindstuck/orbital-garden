# From Beginner Python to Understanding `ai-stack`

A hands-on course for beginning Python developers and AI engineers. By the end, you should be able to trace a text or voice turn through this repository, explain its design choices, run its GPU-free tests, and propose and verify a small improvement at the right boundary.

**Scope:** This course describes the *current* repository. The browser voice/text client, FastAPI/WebSocket server, faster-whisper STT, llama.cpp LLM adapter, Piper TTS and optional in-memory history are implemented. PostgreSQL-backed memory, wake word, chat tool calls and a coding agent are **not** operational. Read [the README](../README.md) and [the backlog](issues.md) before treating any future feature as available.

## How to use this course

- **Starting point:** You can edit files and run Python, but may be new to functions, classes, HTTP and ML inference. No GPU is required for lessons 1–10 or the first capstone option.
- **Pace:** 10 lessons at roughly 2–4 hours each, then a capstone. Work in order; each lesson has a reading path, a practical exercise and an observable completion check. Write your answers in your own notes; do not modify the application just to complete reading exercises.
- **Equipment:** Python 3.11, a terminal, Git and a code editor. Docker Compose v2 and an NVIDIA GPU/toolkit are needed only for the optional real-model run. Paths below are relative to the repository root unless a command first changes directory.
- **Working convention:** Use `py-server` as the current directory when importing application modules or running its tests. On Windows PowerShell, activate a virtual environment with `.venv\Scripts\Activate.ps1`; on POSIX shells, use `. .venv/bin/activate`. If activation is restricted, invoke the environment's `python` directly.

### Set up a GPU-free study environment

```sh
cd py-server
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements-dev.txt
python -m pytest
```

The dev requirements include FastAPI and httpx for the WebSocket tests but **not** the Whisper/Piper runtime stack. The tests inject fake providers and do not import `main.py`; importing `main.py` creates real adapters. For a real deployment, follow [the README setup](../README.md#setup), including the external GGUF model, voice files and CUDA assets. Do not add those assets, `.env`, recordings, database state or keys to Git.

## Learning map

| Stage | Lessons | What you will be able to do |
| --- | --- | --- |
| Python foundations | 1–2 | Read typed Python, iterators, protocols, configuration and tests. |
| Application boundaries | 3–4 | Follow a request through the browser, WebSocket edge and coordinator. |
| AI and audio pipeline | 5–7 | Explain STT, LLM streaming, chunking, TTS, model assets and latency. |
| Systems engineering | 8–10 | Reason about concurrency, state, privacy, deployment and future capabilities. |
| Synthesis | Capstone | Defend a complete turn trace and validate one change or design. |

## Lesson 1 — Python by reading small contracts

**Concepts:** functions, parameters, return values, `None`, exceptions, immutable `@dataclass` objects, type annotations, `Protocol`, and generators (`yield`). A type hint documents intent; Python does not automatically enforce it at runtime.

**Read:** [`providers/base.py`](../py-server/providers/base.py), [`api/protocol.py`](../py-server/api/protocol.py), and [`tests/test_protocol.py`](../py-server/tests/test_protocol.py).

**Try:** From `py-server`, start `python` and enter:

```python
from api.protocol import parse_text_message
parse_text_message('{"type":"text","turn_id":"t1","text":"hello"}')
```

Then pass an empty `text` and observe `ProtocolError`. Sketch the shapes of `TextTurn`, `TranscriptionResult` and `SynthesisResult`. Explain why `TranscriptionResult(text=None, error="no speech detected")` differs from a successful empty string.

**Check:** You can identify where invalid wire input becomes an exception, where a provider reports failure as a typed result, and why `LLMProvider.stream_chat` returns an `Iterator[str]` instead of one finished string.

## Lesson 2 — Configuration, composition and test doubles

**Concepts:** environment variables, validation, dependency injection, structural interfaces, test fakes and unit tests. A composition root chooses concrete implementations; the business logic should depend on their narrow contracts.

**Read:** [`config.py`](../py-server/config.py), [`personas.py`](../py-server/personas.py), [`main.py`](../py-server/main.py), [`tests/test_config.py`](../py-server/tests/test_config.py), and [`tests/test_coordinator.py`](../py-server/tests/test_coordinator.py).

**Try:** In `py-server`, run `python -m pytest tests/test_config.py tests/test_coordinator.py -q`. With `Settings.from_env({"MAX_GPU_CONCURRENCY": "0"})`, predict and then check the failure in a Python REPL. Draw the arrows `Settings -> main.py -> concrete providers/store -> AssistantCoordinator -> create_app`. Substitute `FakeLLM` from the test in your mental model: which application files would need changing to use a different model service?

**Check:** You can explain `SYSTEM_PROMPT` overriding `PERSONA`, why fakes make the coordinator testable without model downloads, and the difference between `Settings.validate()` accepting a backend name and `build_store()` actually implementing it.

## Lesson 3 — Browser, HTTP, WebSocket and the wire contract

**Concepts:** HTTP delivers the page; WebSocket maintains a bidirectional connection. Text frames carry JSON control events; binary frames carry audio bytes. A `turn_id` correlates events, while a `conversation_id` groups history within a connection.

**Read:** [`web/index.html`](../py-server/web/index.html), [`web/app.js`](../py-server/web/app.js), [`api/protocol.py`](../py-server/api/protocol.py), [`api/server.py`](../py-server/api/server.py), and [`tests/test_server.py`](../py-server/tests/test_server.py).

**Try:** Draw two message timelines:

```text
Text:  client JSON text -> server status(thinking) -> status(speaking)
       -> binary WAV chunk(s) -> status(idle)
Voice: client JSON audio_start -> binary recorded audio -> JSON audio_end
       -> status(transcribing) -> transcript -> thinking -> WAV chunk(s) -> idle
```

Mark which voice frames are WebM input and which reply frames are WAV output. Locate the size limits and origin check; run `python -m pytest tests/test_protocol.py tests/test_server.py -q` from `py-server`.

**Check:** You can explain why `ws` versus `wss` depends on the page scheme, why a binary frame before `audio_start` gets `no_audio_turn`, and why an origin check is **not** authentication. Note one contract gap worth investigating: `_finish_audio` does not compare the incoming `turn_id` with the active audio turn's ID.

## Lesson 4 — Orchestration and conversation context

**Concepts:** separation of transport and business logic, chat roles (`system`, `user`, `assistant`), context windows, bounded history, generators that stream results, and failure propagation.

**Read:** [`pipeline/coordinator.py`](../py-server/pipeline/coordinator.py), [`providers/base.py`](../py-server/providers/base.py), [`store/base.py`](../py-server/store/base.py), and the tests for coordinator and store.

**Try:** Trace `AssistantCoordinator.stream_reply("hello", conversation_id)` line by line. Record the exact message list sent to the LLM with (a) no store and (b) two earlier messages in the memory store. Explain when the new user message is appended and when the synthesized assistant text is appended. Run `python -m pytest tests/test_coordinator.py tests/test_store.py -q`.

**Check:** You can state why a system prompt is sent every turn, why history is read *before* the current user message is appended, and what happens to stored assistant history if TTS fails partway through a reply. Distinguish this from persistent long-term memory.

## Lesson 5 — Speech-to-text and audio capture

**Concepts:** browser microphone permissions, `MediaRecorder`, MIME/container formats, buffered frames, in-memory decoding, voice activity detection (VAD), and model inference. Recorded audio is a different artifact from the response audio.

**Read:** the recording functions in [`web/app.js`](../py-server/web/app.js), `_AudioTurn` and `_finish_audio` in [`api/server.py`](../py-server/api/server.py), and [`providers/whisper_stt.py`](../py-server/providers/whisper_stt.py).

**Try:** Draw `getUserMedia -> MediaRecorder -> audio_start -> audio bytes -> audio_end -> WhisperSTT.transcribe -> transcript`. Point out where the 1 MB/frame and 20 MB/turn limits apply, and why `io.BytesIO` avoids writing a shared scratch file. Explain what happens for an empty recording or audio with no detected speech.

**Check:** You can distinguish the declared MIME type from verified media content, identify the first place audio bytes are assembled, and explain why STT can be used only for a voice turn while a text turn skips it. A real microphone/Whisper experiment is optional and needs runtime dependencies and assets.

## Lesson 6 — LLM inference, prompts and streaming text

**Concepts:** local inference versus an API client, GGUF model assets, a llama.cpp server exposing an OpenAI-compatible chat endpoint, sampling parameters, token/text deltas, and first-response latency. “OpenAI-compatible” describes an HTTP interface here; it does not mean requests go to OpenAI's hosted service.

**Read:** [`providers/llama_llm.py`](../py-server/providers/llama_llm.py), [`config.py`](../py-server/config.py), [`personas.py`](../py-server/personas.py), and the `llama-server` section of [`compose.yaml`](../compose.yaml).

**Try:** Map `ChatMessage` objects to the `messages` payload in `chat.completions.create(stream=True)`. Identify `LLM_API_URL`, `LLM_MODEL`, `temperature`, `top_p`, `max_tokens` and `extra_body`. Explain why `-ngl 24` and `-c 8192` in Compose are llama.cpp runtime options rather than Python flags. Note that a persona named `coding` changes the prompt, not the mounted GGUF model or the availability of file/command tools.

**Check:** You can describe the difference between the configured model name sent in an API call and the GGUF file loaded by the service, and explain why the adapter yields only nonempty delta content.

## Lesson 7 — Chunking and text-to-speech

**Concepts:** incremental parsing, sentence boundaries, latency versus naturalness, markdown-to-speech rendering, WAV format, bytes streams and playback queues.

**Read:** [`pipeline/chunking.py`](../py-server/pipeline/chunking.py), [`providers/piper_tts.py`](../py-server/providers/piper_tts.py), the playback functions in [`web/app.js`](../py-server/web/app.js), and [`tests/test_chunking.py`](../py-server/tests/test_chunking.py).

**Try:** In `py-server`, run `python -m pytest tests/test_chunking.py -q`. Predict the chunks from `chunk_text(["Dr. Li found 3.", "14 samples. ", "Read [notes](https://example.com). "])`, then check in a REPL. Follow each emitted phrase through Piper's in-memory WAV creation to the browser's ordered playback buffer. Identify why a buffer of unpunctuated text must flush eventually (`HARD_FLUSH_CHARS`).

**Check:** You can explain why splitting at every period would harm speech, why empty rendered chunks are skipped, and why synthesizing and queuing multiple chunks reduces time to first audio without guaranteeing instant playback.

## Lesson 8 — Async I/O, threads and resource limits

**Concepts:** `async`/`await`, blocking inference, thread pools, `asyncio.to_thread`, thread-to-event-loop communication, semaphore-controlled GPU turns, cancellation and backpressure.

**Read:** `_finish_audio`, `_run_turn` and `_produce` in [`api/server.py`](../py-server/api/server.py), plus the model/voice locking in [`providers/whisper_stt.py`](../py-server/providers/whisper_stt.py) and [`providers/piper_tts.py`](../py-server/providers/piper_tts.py).

**Try:** Draw two lanes (event loop and worker thread). Place Whisper transcription, LLM streaming, Piper synthesis, queue operations and WebSocket sends in the correct lane. Explain what `asyncio.Semaphore(settings.max_gpu_concurrency)` limits. Estimate first-audio latency as transcription time (voice only) + time for enough LLM text to form a speech chunk + synthesis time + network/playback overhead; identify which steps are overlapped and which are sequential.

**Check:** You can point out that STT is offloaded with `to_thread` but happens **before** the GPU turn semaphore, and that the producer-to-consumer `asyncio.Queue` is currently unbounded. Discuss why disconnect cancellation may not instantly stop an already-blocking provider call. These observations are analysis prompts, not claims that those paths have been fixed.

## Lesson 9 — State, memory and privacy

**Concepts:** per-connection identity, short-term context versus persistence, retention, ordering, database migrations, opt-in storage and local data boundaries.

**Read:** [`store/memory.py`](../py-server/store/memory.py), [`store/__init__.py`](../py-server/store/__init__.py), [`store/migrations/0001_init.sql`](../py-server/store/migrations/0001_init.sql), [migration workflow](../py-server/store/migrations/README.md), and [ADR 0002](decisions/0002-storage-and-memory.md).

**Try:** Explain the effect of `STORE_BACKEND=none`, `memory` and `postgres`. For `memory`, follow a fresh WebSocket connection's generated `conversation_id`, a bounded `history()` lookup, an append and a disconnect. Compare `deque(maxlen=200)` to `HISTORY_MAX_MESSAGES=20`: one bounds retained messages per conversation, the other bounds messages included in a prompt. Explain the SQL foreign key with `ON DELETE CASCADE` and the purpose of `schema_migrations`.

**Check:** You can say precisely why starting the `db` Compose profile does not make the application persist chats (`build_store("postgres")` raises `ConfigError`), why a restart loses in-memory state, and why pgvector alone does not implement retrieval. Examine retention across *many* distinct connections as an open design question.

## Lesson 10 — Deployment, access boundaries and future capabilities

**Concepts:** Docker image versus bind mount versus named volume, internal Compose service DNS, published versus exposed ports, environment files, TLS termination, access control versus authentication, tool schemas and capability boundaries.

**Read:** [`compose.yaml`](../compose.yaml), [`py-server/Dockerfile`](../py-server/Dockerfile), [`py-server/docker-entrypoint.sh`](../py-server/docker-entrypoint.sh), [`tools/registry.py`](../py-server/tools/registry.py), [ADR 0001](decisions/0001-network-and-tls.md), [ADR 0003](decisions/0003-wake-word-and-activation.md), [ADR 0004](decisions/0004-coding-agent-boundary.md), and [issues.md](issues.md).

**Try:** Sketch three zones: browser/LAN, `py-server`'s published port, and internal `llama-server`/optional `db` on the Compose network. Locate the bind mounts for code/model/voice/CUDA libraries and the named volumes for caches/DB state. Compare the `current_time` registry entry with an actual chat tool call: where is the registry created, and where is it *not* called? Explain what would have to change before a coding agent could read or write files. If Docker is installed, run `docker compose config` from the repo root after creating a local `.env` from `.env.example`; the validation does not start GPU services.

**Check:** You can tell a reviewer which host port is public by default (`8400`), where internal LLM requests go (`http://llama-server:8000/v1`), why TLS is opt-in, and why neither a wake word nor a system prompt grants filesystem access. Do not copy real secrets into coursework.

## Capstone — Demonstrate deep project understanding

Choose **one** implementation track and complete the shared architecture deliverable. Work in a branch if you intend to keep code changes.

1. **Architecture deliverable (everyone):** Draw a complete voice-turn sequence from microphone capture to ordered WAV playback. Label `turn_id`, `conversation_id`, JSON versus binary frames, the point where STT can fail, the message list sent to the LLM, the sentence chunker and the storage mode. Add a text-turn trace showing the skipped STT step. Annotate which operations block in a worker, which are awaited at the edge and where the GPU semaphore applies.
2. **Implementation track A (GPU-free):** Extend a fake-provider test in `py-server/tests/test_server.py` to cover a real contract edge case (for example, an empty audio turn or an oversized frame). State expected status/error events before writing the test, then run `python -m pytest` from `py-server`. If the test reveals a bug, make the smallest fix in the layer that owns the contract and explain the change. Avoid tests that simply duplicate an existing assertion.
3. **Implementation track B (design-only):** Specify an improvement to bounded streaming/backpressure or to Postgres persistence. Identify the owning module, inputs/outputs, failures, resource limits and two meaningful tests. Clearly label it **proposed**; do not imply the feature already exists.
4. **Review:** Explain two trade-offs (for example, low first-audio latency versus chunk quality, or ephemeral privacy versus recall) and distinguish a currently implemented control from a remaining limitation in [issues.md](issues.md).

**Completion rubric:** Another developer can reproduce your GPU-free test result or follow your design; your diagram correctly names every boundary and payload format; you cite the code owning each decision; and your account of `none`/`memory`/`postgres`, tools, wake word and coding-agent status matches the running application. For code changes, also run `ruff check .`, `mypy .` and `python -m pytest` from `py-server` (and `ruff format --check .` if you changed Python formatting).

### Optional hardware lab: real end-to-end run

After following the [README prerequisites and setup](../README.md#prerequisites), start with `docker compose up -d --build` from the repo root. Open `http://<host>:8400/`, try one typed turn and one press-to-talk turn, and compare observed status/transcript/audio events to your diagrams. This lab requires compatible GPU drivers/toolkit, a local GGUF file, a Piper voice and the documented CUDA runtime assets. Finish with `docker compose down`. The GPU-free capstone is sufficient to complete the course.

## Further reading in this repository

- [README](../README.md): runnable architecture, deployment and troubleshooting.
- [Decision records](decisions/README.md): accepted network/storage choices and proposed activation/capability boundaries.
- [Known issues](issues.md): implementation gaps to investigate; prefer these over assumptions from older plans.
- [`py-server/tests/`](../py-server/tests/): examples of protocol, chunking, config, store and edge tests using fakes.
- [Historical refactoring plan](refactoring_1_plan.md): motivation for boundaries; it is a plan from an earlier state of the project, not a description of current behavior.
