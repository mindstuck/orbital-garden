"""Piper text-to-speech adapter.

The voice is loaded once and synthesis is serialized because a single ONNX
voice object is shared across requests. Output is produced in memory.
"""
from __future__ import annotations

import io
import logging
import os
import threading
import wave

from piper import PiperVoice

from .base import SynthesisResult

logger = logging.getLogger(__name__)


class PiperTTS:
    def __init__(self, voice_path: str = "./voices/hal.onnx") -> None:
        self._voice_path = voice_path
        self._voice: PiperVoice | None = None
        self._load_lock = threading.Lock()
        self._synth_lock = threading.Lock()

    def _get_voice(self) -> PiperVoice:
        if self._voice is None:
            with self._load_lock:
                if self._voice is None:
                    if not os.path.isfile(self._voice_path):
                        raise FileNotFoundError(
                            f"Piper voice not found: {self._voice_path}. "
                            "See py-server/voices/README.md."
                        )
                    self._voice = PiperVoice.load(self._voice_path)
                    logger.info("Loaded Piper voice from %s", self._voice_path)
        return self._voice

    def synthesize(self, text: str) -> SynthesisResult:
        if not text or not text.strip():
            return SynthesisResult(audio=None, error="empty text")

        try:
            voice = self._get_voice()
            buffer = io.BytesIO()
            with self._synth_lock:
                with wave.open(buffer, "wb") as wav_file:
                    voice.synthesize_wav(text, wav_file)
            return SynthesisResult(audio=buffer.getvalue())
        except Exception as exc:  # noqa: BLE001 - returned as a typed error
            logger.exception("generate_audio error")
            return SynthesisResult(audio=None, error=str(exc))
