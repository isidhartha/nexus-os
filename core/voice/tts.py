"""Text-to-speech using pyttsx3 with voice selection and graceful fallback."""

from __future__ import annotations

import threading
from typing import List, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class TextToSpeech:
    """Speaks text aloud using pyttsx3 (offline, no API required)."""

    def __init__(
        self,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        voice_id: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.rate = rate or settings.tts_rate
        self.volume = volume or settings.tts_volume
        self.voice_id = voice_id
        self._engine = None
        self._lock = threading.Lock()
        self._available = False
        self._init_engine()

    def _init_engine(self) -> None:
        try:
            import pyttsx3  # type: ignore[import]

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)

            if self.voice_id:
                self._engine.setProperty("voice", self.voice_id)
            else:
                self._select_default_voice()

            self._available = True
            logger.info("pyttsx3 TTS engine initialized (rate=%d)", self.rate)
        except ImportError:
            logger.warning("pyttsx3 not installed — TTS in mock mode")
        except Exception as exc:
            logger.error("TTS init error: %s", exc)

    def _select_default_voice(self) -> None:
        if not self._engine:
            return
        voices = self._engine.getProperty("voices")
        for voice in voices or []:
            if "english" in voice.name.lower() or "en" in (voice.id or "").lower():
                self._engine.setProperty("voice", voice.id)
                logger.debug("Selected voice: %s", voice.name)
                return

    def speak(self, text: str, block: bool = False) -> None:
        """Speak the given text. Non-blocking by default."""
        if not text.strip():
            return

        if not self._available or self._engine is None:
            logger.info("[TTS Mock] %s", text)
            return

        if block:
            self._speak_sync(text)
        else:
            thread = threading.Thread(
                target=self._speak_sync, args=(text,), daemon=True
            )
            thread.start()

    def _speak_sync(self, text: str) -> None:
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as exc:
                logger.error("TTS speak error: %s", exc)

    def stop(self) -> None:
        if self._engine and self._available:
            try:
                self._engine.stop()
            except Exception:
                pass

    def list_voices(self) -> List[dict]:
        if not self._engine:
            return []
        voices = self._engine.getProperty("voices") or []
        return [{"id": v.id, "name": v.name, "languages": v.languages} for v in voices]

    def set_voice(self, voice_id: str) -> bool:
        if not self._engine:
            return False
        try:
            self._engine.setProperty("voice", voice_id)
            self.voice_id = voice_id
            return True
        except Exception as exc:
            logger.error("Failed to set voice: %s", exc)
            return False

    @property
    def is_available(self) -> bool:
        return self._available


_tts_instance: Optional[TextToSpeech] = None


def get_tts() -> TextToSpeech:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    return _tts_instance
