"""FastAPI/WebSocket edge for py-server.

Only transport concerns live here: HTTP static delivery, the WebSocket
contract, per-connection state, concurrency limiting and error framing.
The assistant logic is delegated to :class:`pipeline.coordinator.AssistantCoordinator`.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import Settings
from pipeline.coordinator import AssistantCoordinator
from tools import ToolRegistry

from .protocol import (
    MAX_AUDIO_FRAME_BYTES,
    MAX_AUDIO_TURN_BYTES,
    AudioEnd,
    AudioStart,
    ProtocolError,
    TextTurn,
    encode_event,
    parse_text_message,
)

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@dataclass
class _AudioTurn:
    turn_id: str
    mime: str
    buffer: bytearray
    size: int = 0


def _suffix_for_mime(mime: str) -> str:
    return {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
    }.get(mime, ".webm")


class _Session:
    """Per-connection turn state and streaming pipeline."""

    def __init__(
        self,
        coordinator: AssistantCoordinator,
        gpu_lock: asyncio.Semaphore,
        conversation_id: str,
    ) -> None:
        self._coordinator = coordinator
        self._gpu_lock = gpu_lock
        self._conversation_id = conversation_id
        self._audio: _AudioTurn | None = None

    async def on_text(self, websocket: WebSocket, raw: str) -> None:
        try:
            event = parse_text_message(raw)
        except ProtocolError as exc:
            await self._send_error(websocket, None, exc)
            return

        if isinstance(event, TextTurn):
            await self._run_turn(websocket, event.turn_id, event.text)
        elif isinstance(event, AudioStart):
            await self._start_audio(websocket, event)
        elif isinstance(event, AudioEnd):
            await self._finish_audio(websocket, event.turn_id)

    async def on_audio_bytes(self, websocket: WebSocket, data: bytes) -> None:
        if self._audio is None:
            await self._send_error(
                websocket, None, ProtocolError("no_audio_turn", "Audio frame without audio_start.")
            )
            return
        if len(data) > MAX_AUDIO_FRAME_BYTES:
            await self._send_error(
                websocket,
                self._audio.turn_id,
                ProtocolError("message_too_large", "Audio frame exceeds the size limit."),
            )
            return
        if self._audio.size + len(data) > MAX_AUDIO_TURN_BYTES:
            await self._send_error(
                websocket,
                self._audio.turn_id,
                ProtocolError("message_too_large", "Audio turn exceeds the size limit."),
            )
            self._audio = None
            return

        self._audio.buffer.extend(data)
        self._audio.size += len(data)

    async def _start_audio(self, websocket: WebSocket, event: AudioStart) -> None:
        self._audio = _AudioTurn(turn_id=event.turn_id, mime=event.mime, buffer=bytearray())
        await websocket.send_text(encode_event("status", turn_id=event.turn_id, state="recording"))

    async def _finish_audio(self, websocket: WebSocket, turn_id: str) -> None:
        if self._audio is None:
            await self._send_error(
                websocket, turn_id, ProtocolError("no_audio_turn", "audio_end without audio_start.")
            )
            return

        audio = self._audio
        self._audio = None

        if audio.size == 0:
            await self._send_error(
                websocket, turn_id, ProtocolError("empty_audio", "No audio received for the turn.")
            )
            return

        await websocket.send_text(encode_event("status", turn_id=turn_id, state="transcribing"))
        result = await asyncio.to_thread(
            self._coordinator.transcribe, bytes(audio.buffer), _suffix_for_mime(audio.mime)
        )
        if not result.ok:
            await self._send_error(
                websocket,
                turn_id,
                ProtocolError("transcription_failed", result.error or "Could not transcribe the audio."),
            )
            return

        await websocket.send_text(encode_event("transcript", turn_id=turn_id, text=result.text))
        await self._run_turn(websocket, turn_id, result.text)

    async def _run_turn(self, websocket: WebSocket, turn_id: str, text: str) -> None:
        await websocket.send_text(encode_event("status", turn_id=turn_id, state="thinking"))

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        cancel = threading.Event()

        async with self._gpu_lock:
            producer = loop.run_in_executor(None, self._produce, loop, queue, cancel, text)
            speaking = False
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    kind, payload = item
                    if kind == "error":
                        await websocket.send_text(
                            encode_event(
                                "error", turn_id=turn_id, code="pipeline_error", message=payload
                            )
                        )
                    elif kind == "audio":
                        if not speaking:
                            await websocket.send_text(
                                encode_event("status", turn_id=turn_id, state="speaking")
                            )
                            speaking = True
                        await websocket.send_bytes(payload)
            except (WebSocketDisconnect, RuntimeError):
                cancel.set()
                raise
            finally:
                cancel.set()
                await producer

        try:
            await websocket.send_text(encode_event("status", turn_id=turn_id, state="idle"))
        except (WebSocketDisconnect, RuntimeError):
            pass

    def _produce(
        self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, cancel: threading.Event, text: str
    ) -> None:
        def emit(item) -> bool:
            if cancel.is_set():
                return False
            try:
                asyncio.run_coroutine_threadsafe(queue.put(item), loop).result()
            except Exception:  # loop closed or cancelled
                cancel.set()
                return False
            return not cancel.is_set()

        try:
            for audio in self._coordinator.stream_reply(text, self._conversation_id):
                if cancel.is_set():
                    break
                if not emit(("audio", audio)):
                    break
        except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to the client
            logger.exception("turn pipeline failed")
            emit(("error", str(exc)))
        finally:
            try:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
            except Exception:
                pass

    async def _send_error(self, websocket: WebSocket, turn_id: str | None, exc: ProtocolError) -> None:
        try:
            await websocket.send_text(
                encode_event("error", turn_id=turn_id, code=exc.code, message=exc.message)
            )
        except (WebSocketDisconnect, RuntimeError):
            pass

    async def aclose(self) -> None:
        self._audio = None


def _origin_allowed(websocket: WebSocket, allowed_origins: tuple[str, ...]) -> bool:
    origin = websocket.headers.get("origin")
    if origin is None:
        # Non-browser clients (CLI, tests) do not send Origin.
        return True
    if allowed_origins:
        return origin in allowed_origins
    origin_host = urlparse(origin).netloc
    return origin_host == websocket.headers.get("host", "")


def create_app(
    settings: Settings,
    coordinator: AssistantCoordinator,
    tools: ToolRegistry | None = None,
) -> FastAPI:
    app = FastAPI(title="ai-stack py-server")
    gpu_lock = asyncio.Semaphore(settings.max_gpu_concurrency)

    # Tool execution is exposed as an extension point; it is not part of the
    # chat loop yet (see docs/decisions/0004-coding-agent-boundary.md).
    app.state.tools = tools

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        if not _origin_allowed(websocket, settings.allowed_origins):
            logger.warning(
                "Rejected WebSocket connection from origin %r",
                websocket.headers.get("origin"),
            )
            await websocket.close(code=1008, reason="origin not allowed")
            return

        await websocket.accept()
        session = _Session(coordinator, gpu_lock, conversation_id=uuid.uuid4().hex)
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                text_data = message.get("text")
                bytes_data = message.get("bytes")
                if text_data is not None:
                    await session.on_text(websocket, text_data)
                elif bytes_data is not None:
                    await session.on_audio_bytes(websocket, bytes_data)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await session.aclose()

    return app
