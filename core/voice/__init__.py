"""NexusOS voice subsystem — STT, TTS, wake word, and identity."""

from .identity import VoiceIdentityManager
from .stt import MicrophoneRecorder, WhisperSTT
from .tts import TextToSpeech, get_tts
from .wake_word import WakeWordDetector

__all__ = [
    "VoiceIdentityManager",
    "MicrophoneRecorder",
    "WhisperSTT",
    "TextToSpeech",
    "get_tts",
    "WakeWordDetector",
]
