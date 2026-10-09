import io
import logging
import time
from dataclasses import dataclass

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Loaded once per process. Faster-whisper models are expensive to construct,
# so they are shared rather than rebuilt per request.
model = WhisperModel(
    "base",
    device="cuda",
    compute_type="float16",
)


@dataclass(frozen=True)
class TranscriptionResult:
    """Typed transcription outcome. `text` is None on failure."""

    text: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.text is not None


def transcribe_audio(audio: bytes, suffix: str = ".webm") -> TranscriptionResult:
    """Transcribe in-memory audio bytes.

    No scratch files are written and raw transcript text is not logged.
    """
    if not audio:
        return TranscriptionResult(text=None, error="empty audio")

    try:
        start_time = time.time()
        stream = io.BytesIO(audio)
        segments, info = model.transcribe(
            stream,
            beam_size=5,
            language="en",
            vad_filter=True,
        )

        text = "".join(segment.text for segment in segments).strip()
        logger.info(
            "Transcribed %.2fs of audio in %.2fs",
            info.duration,
            time.time() - start_time,
        )

        if not text:
            return TranscriptionResult(text=None, error="no speech detected")
        return TranscriptionResult(text=text)
    except Exception as exc:  # noqa: BLE001 - returned to the caller as a typed error
        logger.exception("transcribe_audio error")
        return TranscriptionResult(text=None, error=str(exc))


if __name__ == "__main__":
    # Local smoke check: reads a pinned sample from disk, never a shared scratch path.
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: python stt.py <audio-file>")
    with open(sys.argv[1], "rb") as handle:
        print(transcribe_audio(handle.read(), suffix=".webm"))
