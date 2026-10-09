import io
import logging
import os
import threading
import wave
from dataclasses import dataclass

from piper import PiperVoice

logger = logging.getLogger(__name__)

DEFAULT_VOICE_PATH = os.getenv("TTS_VOICE_PATH", "./voices/hal.onnx")

# The Piper voice is loaded once and reused. Synthesis is serialized because a
# single ONNX voice object is shared across requests.
_voice: PiperVoice | None = None
_voice_lock = threading.Lock()
_synth_lock = threading.Lock()


@dataclass(frozen=True)
class SynthesisResult:
    """Typed synthesis outcome. `audio` is None on failure."""

    audio: bytes | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.audio is not None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        with _voice_lock:
            if _voice is None:
                if not os.path.isfile(DEFAULT_VOICE_PATH):
                    raise FileNotFoundError(
                        f"Piper voice not found: {DEFAULT_VOICE_PATH}. "
                        "See py-server/voices/README.md."
                    )
                _voice = PiperVoice.load(DEFAULT_VOICE_PATH)
                logger.info("Loaded Piper voice from %s", DEFAULT_VOICE_PATH)
    return _voice


def generate_audio(text: str) -> SynthesisResult:
    """Synthesize WAV bytes for a text chunk.

    Output is produced in memory; no shared `test.wav` scratch file is used.
    """
    if not text or not text.strip():
        return SynthesisResult(audio=None, error="empty text")

    try:
        voice = _get_voice()
        buffer = io.BytesIO()
        with _synth_lock:
            with wave.open(buffer, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        return SynthesisResult(audio=buffer.getvalue())
    except Exception as exc:  # noqa: BLE001 - returned to the caller as a typed error
        logger.exception("generate_audio error")
        return SynthesisResult(audio=None, error=str(exc))


if __name__ == "__main__":
    result = generate_audio("Welcome to the world of speech synthesis.")
    print(f"ok={result.ok} bytes={len(result.audio) if result.audio else 0}")
