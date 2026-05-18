"""Speech-to-text using OpenAI Whisper with graceful fallback."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class WhisperSTT:
    """Transcribes audio to text using the Whisper model."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.whisper_model
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            import whisper  # type: ignore[import]
            self._model = whisper.load_model(self.model_name)
            self._available = True
            logger.info("Whisper model '%s' loaded", self.model_name)
        except ImportError:
            logger.warning("openai-whisper not installed — STT in mock mode")
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)

    def transcribe_file(self, audio_path: str | Path) -> str:
        """Transcribe an audio file and return the text."""
        if not self._available or self._model is None:
            return self._mock_transcribe()

        try:
            import whisper  # type: ignore[import]

            result = self._model.transcribe(
                str(audio_path),
                language="en",
                fp16=False,
            )
            text = result.get("text", "").strip()
            logger.debug("Transcribed: %s", text)
            return text
        except Exception as exc:
            logger.error("Transcription error: %s", exc)
            return ""

    def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".wav") -> str:
        """Transcribe raw audio bytes."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            return self.transcribe_file(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def transcribe_numpy(self, audio_array: "np.ndarray") -> str:  # type: ignore[name-defined]
        """Transcribe a numpy float32 audio array (sample_rate=16000)."""
        if not self._available or self._model is None:
            return self._mock_transcribe()

        try:
            result = self._model.transcribe(audio_array, language="en", fp16=False)
            return result.get("text", "").strip()
        except Exception as exc:
            logger.error("Transcription error: %s", exc)
            return ""

    def _mock_transcribe(self) -> str:
        return "[STT unavailable — Whisper not installed]"

    @property
    def is_available(self) -> bool:
        return self._available


class MicrophoneRecorder:
    """Record audio from microphone for a given duration."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self._available = False
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            import sounddevice  # type: ignore[import]
            self._available = True
        except ImportError:
            logger.warning("sounddevice not installed — microphone recording unavailable")

    def record(self, duration: float = 5.0) -> Optional["np.ndarray"]:  # type: ignore[name-defined]
        if not self._available:
            return None
        try:
            import sounddevice as sd  # type: ignore[import]
            import numpy as np

            logger.debug("Recording %.1fs of audio", duration)
            audio = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            return audio.flatten()
        except Exception as exc:
            logger.error("Recording error: %s", exc)
            return None

    @property
    def is_available(self) -> bool:
        return self._available
