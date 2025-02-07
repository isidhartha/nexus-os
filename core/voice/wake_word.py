"""Wake word detection for NexusOS.

Primary: pvporcupine (if installed and access key configured).
Fallback: lightweight keyword matching on Whisper transcriptions.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    """Detects wake word via Porcupine or keyword fallback."""

    def __init__(
        self,
        wake_word: Optional[str] = None,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        settings = get_settings()
        self.wake_word = (wake_word or settings.wake_word).lower()
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._porcupine = None
        self._use_porcupine = False
        self._init_detector()

    def _init_detector(self) -> None:
        try:
            import pvporcupine  # type: ignore[import]
            import struct
            self._pvporcupine = pvporcupine
            self._struct = struct
            self._use_porcupine = True
            logger.info("Porcupine wake word engine available")
        except ImportError:
            logger.info("Porcupine not installed — using keyword fallback mode")
            self._use_porcupine = False

    def check_phrase(self, text: str) -> bool:
        """Return True if the wake word is found in the transcribed text."""
        return self.wake_word in text.lower()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._use_porcupine:
            self._thread = threading.Thread(
                target=self._porcupine_loop, daemon=True
            )
        else:
            self._thread = threading.Thread(
                target=self._keyword_loop, daemon=True
            )
        self._thread.start()
        logger.info("Wake word detector started (word=%s)", self.wake_word)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Wake word detector stopped")

    def _porcupine_loop(self) -> None:
        """Run porcupine detection in a blocking thread."""
        try:
            import pvporcupine
            import pyaudio  # type: ignore[import]

            porcupine = pvporcupine.create(keywords=[self.wake_word])
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length,
            )
            logger.info("Porcupine listening for '%s'", self.wake_word)
            while self._running:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = self._struct.unpack_from(
                    "h" * porcupine.frame_length, pcm
                )
                result = porcupine.process(pcm)
                if result >= 0:
                    logger.info("Wake word detected!")
                    if self.callback:
                        self.callback()
        except Exception as exc:
            logger.warning("Porcupine loop error: %s — falling back", exc)
            self._keyword_loop()

    def _keyword_loop(self) -> None:
        """Fallback: periodically transcribe mic chunks and check for wake word."""
        try:
            import whisper  # type: ignore[import]
            import sounddevice as sd  # type: ignore[import]
            import numpy as np

            model = whisper.load_model("tiny")
            sample_rate = 16000
            chunk_seconds = 2
            logger.info("Keyword fallback listening for '%s'", self.wake_word)

            while self._running:
                audio = sd.rec(
                    int(chunk_seconds * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
                audio_flat = audio.flatten()
                result = model.transcribe(audio_flat, language="en", fp16=False)
                text = result.get("text", "").strip().lower()
                if text and self.check_phrase(text):
                    logger.info("Wake word detected in: '%s'", text)
                    if self.callback:
                        self.callback()
        except Exception as exc:
            logger.error("Keyword fallback loop error: %s", exc)

    @property
    def is_running(self) -> bool:
        return self._running
