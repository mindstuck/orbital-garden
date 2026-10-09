"""Faster-whisper speech-to-text adapter."""

from __future__ import annotations

import io
import logging
import threading
import time

from faster_whisper import WhisperModel

from .base import TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Transcribe in-memory audio with a lazily loaded faster-whisper model.

    The model is constructed once per process and shared across requests.
    """

    def __init__(
        self,
        model_name: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "en",
        beam_size: int = 5,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._beam_size = beam_size
        self._model: WhisperModel | None = None
        self._load_lock = threading.Lock()

    def _load(self) -> WhisperModel:
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    logger.info(
                        "Loading faster-whisper model %s on %s (%s)",
                        self._model_name,
                        self._device,
                        self._compute_type,
                    )
                    self._model = WhisperModel(
                        self._model_name,
                        device=self._device,
                        compute_type=self._compute_type,
                    )
        return self._model

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> TranscriptionResult:
        if not audio:
            return TranscriptionResult(text=None, error="empty audio")

        try:
            start_time = time.time()
            segments, info = self._load().transcribe(
                io.BytesIO(audio),
                beam_size=self._beam_size,
                language=self._language,
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
        except Exception as exc:  # noqa: BLE001 - returned as a typed error
            logger.exception("transcribe_audio error")
            return TranscriptionResult(text=None, error=str(exc))
