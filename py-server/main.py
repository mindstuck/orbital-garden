import asyncio
import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from llm import get_response
from protocol import (
    MAX_AUDIO_FRAME_BYTES,
    MAX_AUDIO_TURN_BYTES,
    AudioEnd,
    AudioStart,
    ProtocolError,
    TextTurn,
    encode_event,
    parse_text_message,
)
from stt import transcribe_audio
from text_chunker import chunk_text
from tts import generate_audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("py_server")

app = FastAPI()

# Single-user, single-GPU machine: serialize model work so extra connections
# queue instead of starving each other.
GPU_TURN_LOCK = asyncio.Semaphore(1)

# Comma-separated list of allowed browser origins. Empty means "same host as
# the request", which is the expected LAN boundary. A WebSocket connection is
# not itself proof of authorization; see docs/issues.md.
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}

html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Assistant</title>
</head>
<body>
    <h1>Assistant</h1>

    <button style="width: 200px; height: 50px;" id="recordButton">Press to Talk</button>

    <input type="text" id="textInput" placeholder="Type a message..." style="width: 300px; height: 30px;">
    <input type="button" value="Send" id="sendButton" style="height: 36px;">

    <div id="status" aria-live="polite"></div>
    <ul id="messages"></ul>

    <script>
        const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(`${wsScheme}://${window.location.host}/ws`);
        ws.binaryType = "arraybuffer";

        const button = document.getElementById("recordButton");
        const textInput = document.getElementById("textInput");
        const sendButton = document.getElementById("sendButton");
        const messages = document.getElementById("messages");
        const statusEl = document.getElementById("status");

        let mediaRecorder = null;
        let mediaStream = null;
        let activeTurnId = null;
        let recording = false;

        let playing = false;
        let currentAudio = null;
        let currentUrl = null;
        const playBuffer = [];

        function newTurnId() {
            if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
            return Math.random().toString(36).slice(2) + Date.now().toString(36);
        }

        function addMessage(text, cls) {
            const li = document.createElement("li");
            li.textContent = text;
            if (cls) li.className = cls;
            messages.appendChild(li);
        }

        function setStatus(text) { statusEl.textContent = text || ""; }

        function safeSend(payload) {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(payload);
                return true;
            }
            return false;
        }

        ws.onmessage = function(event) {
            if (typeof event.data === "string") {
                handleEvent(event.data);
            } else {
                playOrQueue(event.data);
            }
        };

        function handleEvent(raw) {
            let msg;
            try { msg = JSON.parse(raw); } catch (e) { return; }
            if (msg.type === "status") {
                setStatus(msg.state || "");
            } else if (msg.type === "transcript") {
                addMessage("You: " + msg.text, "transcript");
            } else if (msg.type === "error") {
                setStatus("");
                addMessage("Error (" + msg.code + "): " + msg.message, "error");
            }
        }

        ws.onclose = function() {
            setStatus("Disconnected");
            cleanupRecording();
            stopPlayback();
        };

        ws.onerror = function() { setStatus("Connection error"); };

        button.onclick = async function() {
            if (recording) {
                stopRecording();
            } else {
                await startRecording();
            }
        };

        sendButton.onclick = sendText;
        textInput.addEventListener("keydown", function(event) {
            if (event.key === "Enter") sendText();
        });

        function sendText() {
            const text = textInput.value.trim();
            if (!text) return;
            const turnId = newTurnId();
            if (safeSend(JSON.stringify({ type: "text", turn_id: turnId, text: text }))) {
                addMessage("You: " + text, "transcript");
                textInput.value = "";
            }
        }

        async function startRecording() {
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err) {
                addMessage("Microphone error: " + err.message, "error");
                return;
            }

            activeTurnId = newTurnId();
            if (!safeSend(JSON.stringify({
                type: "audio_start",
                turn_id: activeTurnId,
                mime: "audio/webm"
            }))) {
                cleanupRecording();
                return;
            }

            mediaRecorder = new MediaRecorder(mediaStream);
            mediaRecorder.ondataavailable = function(event) {
                if (event.data && event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    ws.send(event.data);
                }
            };
            mediaRecorder.onstop = function() {
                if (activeTurnId) {
                    safeSend(JSON.stringify({ type: "audio_end", turn_id: activeTurnId }));
                }
                activeTurnId = null;
                cleanupRecording();
            };

            mediaRecorder.start(250);
            recording = true;
            button.textContent = "Press to Send";
            setStatus("recording");
        }

        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                recording = false;
                button.textContent = "Press to Talk";
                setStatus("");
                mediaRecorder.stop();
            }
        }

        function cleanupRecording() {
            recording = false;
            if (mediaStream) {
                mediaStream.getTracks().forEach(function(track) { track.stop(); });
                mediaStream = null;
            }
            mediaRecorder = null;
            activeTurnId = null;
            button.textContent = "Press to Talk";
        }

        function playOrQueue(data) {
            if (playing) {
                playBuffer.push(data);
            } else {
                playWav(data);
            }
        }

        function playWav(rawData) {
            playing = true;
            const blob = rawData instanceof Blob
                ? rawData
                : new Blob([rawData], { type: "audio/wav" });

            currentUrl = URL.createObjectURL(blob);
            const audio = new Audio(currentUrl);
            currentAudio = audio;

            const finish = function() {
                if (currentUrl) URL.revokeObjectURL(currentUrl);
                currentUrl = null;
                currentAudio = null;
                const next = playBuffer.shift();
                if (next) {
                    playWav(next);
                } else {
                    playing = false;
                }
            };

            audio.onended = finish;
            audio.onerror = finish;
            audio.play().catch(function(error) {
                console.error("Failed to play audio:", error);
                finish();
            });
        }

        function stopPlayback() {
            playBuffer.length = 0;
            if (currentAudio) {
                try { currentAudio.pause(); } catch (e) { /* ignore */ }
            }
            if (currentUrl) URL.revokeObjectURL(currentUrl);
            currentAudio = null;
            currentUrl = null;
            playing = false;
        }

        window.addEventListener("beforeunload", function() {
            stopPlayback();
            cleanupRecording();
            try { ws.close(); } catch (e) { /* ignore */ }
        });
    </script>
</body>
</html>
"""


def _origin_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if origin is None:
        # Non-browser clients (CLI, tests) do not send Origin.
        return True
    if ALLOWED_ORIGINS:
        return origin in ALLOWED_ORIGINS
    origin_host = urlparse(origin).netloc
    return origin_host == websocket.headers.get("host", "")


@dataclass
class _AudioTurn:
    turn_id: str
    mime: str
    path: str
    size: int = 0


class _Session:
    """Per-connection turn state and streaming pipeline."""

    def __init__(self) -> None:
        self._audio: _AudioTurn | None = None
        self._handle = None

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
            await self._discard_audio()
            return

        if self._handle is None:
            self._handle = open(self._audio.path, "ab")
        self._handle.write(data)
        self._audio.size += len(data)

    async def _start_audio(self, websocket: WebSocket, event: AudioStart) -> None:
        await self._discard_audio()
        fd, path = tempfile.mkstemp(prefix="turn-", suffix=".webm")
        os.close(fd)
        self._audio = _AudioTurn(turn_id=event.turn_id, mime=event.mime, path=path)
        self._handle = open(path, "wb")
        await websocket.send_text(encode_event("status", turn_id=event.turn_id, state="recording"))

    async def _finish_audio(self, websocket: WebSocket, turn_id: str) -> None:
        if self._audio is None:
            await self._send_error(
                websocket, turn_id, ProtocolError("no_audio_turn", "audio_end without audio_start.")
            )
            return

        audio = self._audio
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        self._audio = None

        try:
            if audio.size == 0:
                await self._send_error(
                    websocket, turn_id, ProtocolError("empty_audio", "No audio received for the turn.")
                )
                return

            await websocket.send_text(encode_event("status", turn_id=turn_id, state="transcribing"))
            text = await asyncio.to_thread(transcribe_audio, audio.path)
            if not text:
                await self._send_error(
                    websocket,
                    turn_id,
                    ProtocolError("transcription_failed", "Could not transcribe the audio."),
                )
                return

            await websocket.send_text(encode_event("transcript", turn_id=turn_id, text=text))
            await self._run_turn(websocket, turn_id, text)
        finally:
            self._remove(audio.path)

    async def _run_turn(self, websocket: WebSocket, turn_id: str, text: str) -> None:
        await websocket.send_text(encode_event("status", turn_id=turn_id, state="thinking"))

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        cancel = threading.Event()

        async with GPU_TURN_LOCK:
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

    @staticmethod
    def _produce(loop, queue: asyncio.Queue, cancel: threading.Event, text: str) -> None:
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
            response_stream = get_response(text)
            for spoken in chunk_text(response_stream):
                if cancel.is_set():
                    break
                audio = generate_audio(spoken)
                if audio and not emit(("audio", audio)):
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

    async def _discard_audio(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        if self._audio is not None:
            self._remove(self._audio.path)
            self._audio = None

    async def aclose(self) -> None:
        await self._discard_audio()

    @staticmethod
    def _remove(path: str | None) -> None:
        if not path:
            return
        try:
            os.remove(path)
        except OSError:
            pass


@app.get("/")
async def get() -> HTMLResponse:
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not _origin_allowed(websocket):
        logger.warning("Rejected WebSocket connection from origin %r", websocket.headers.get("origin"))
        await websocket.close(code=1008, reason="origin not allowed")
        return

    await websocket.accept()
    session = _Session()
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


if __name__ == "__main__":
    # Must bind to 0.0.0.0 inside the container
    uvicorn.run(app, host="0.0.0.0", port=8000)
