"""Voice identity recognition — speaker enrollment and identification."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..shared.config import get_settings
from ..shared.logging import get_logger
from ..shared.models import VoiceProfile

logger = get_logger(__name__)

_PROFILES_PATH = Path("./data/voice_profiles.json")


def _extract_features(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """Extract a simple MFCC-like feature vector from audio (no external lib required)."""
    try:
        from scipy.fftpack import dct  # type: ignore[import]

        frame_size = int(0.025 * sample_rate)
        hop_size = int(0.010 * sample_rate)
        n_mfcc = 13

        frames = [
            audio[i : i + frame_size]
            for i in range(0, len(audio) - frame_size, hop_size)
        ]
        if not frames:
            return np.zeros(n_mfcc)

        features = []
        for frame in frames:
            frame = frame * np.hamming(len(frame))
            power = np.abs(np.fft.rfft(frame)) ** 2
            n_filters = 26
            filters = np.zeros((n_filters, len(power)))
            for m in range(n_filters):
                filters[m, max(0, m * 2) : min(m * 2 + 3, len(power))] = 1
            mel = np.log(np.dot(filters, power) + 1e-10)
            mfcc = dct(mel)[:n_mfcc]
            features.append(mfcc)

        return np.mean(features, axis=0)
    except Exception:
        return np.random.rand(13)


class VoiceIdentityManager:
    """Manages speaker profiles for identity recognition."""

    def __init__(self) -> None:
        self._profiles: Dict[str, VoiceProfile] = {}
        self._load_profiles()

    def _load_profiles(self) -> None:
        _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _PROFILES_PATH.exists():
            try:
                raw = json.loads(_PROFILES_PATH.read_text())
                for p in raw:
                    profile = VoiceProfile(**p)
                    self._profiles[profile.id] = profile
                logger.info("Loaded %d voice profiles", len(self._profiles))
            except Exception as exc:
                logger.error("Failed to load voice profiles: %s", exc)

    def _save_profiles(self) -> None:
        _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = [p.model_dump(mode="json") for p in self._profiles.values()]
        _PROFILES_PATH.write_text(json.dumps(data, indent=2, default=str))

    def enroll(
        self,
        name: str,
        audio_samples: List[np.ndarray],
        sample_rate: int = 16000,
    ) -> VoiceProfile:
        """Enroll a new speaker from multiple audio samples."""
        all_features = [_extract_features(a, sample_rate) for a in audio_samples]
        avg_features = np.mean(all_features, axis=0).tolist()

        profile = VoiceProfile(
            id=str(uuid.uuid4()),
            name=name,
            features=avg_features,
            created_at=datetime.utcnow(),
        )
        self._profiles[profile.id] = profile
        self._save_profiles()
        logger.info("Enrolled speaker: %s (id=%s)", name, profile.id)
        return profile

    def identify(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.75,
    ) -> Optional[Tuple[VoiceProfile, float]]:
        """Identify the speaker from audio. Returns (profile, confidence) or None."""
        if not self._profiles:
            return None

        features = _extract_features(audio, sample_rate)
        best_score = -1.0
        best_profile = None

        for profile in self._profiles.values():
            ref = np.array(profile.features)
            norm_f = np.linalg.norm(features)
            norm_r = np.linalg.norm(ref)
            if norm_f == 0 or norm_r == 0:
                continue
            score = float(np.dot(features, ref) / (norm_f * norm_r))
            if score > best_score:
                best_score = score
                best_profile = profile

        if best_profile and best_score >= threshold:
            best_profile.last_seen = datetime.utcnow()
            self._save_profiles()
            return best_profile, best_score

        return None

    def list_profiles(self) -> List[VoiceProfile]:
        return list(self._profiles.values())

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._save_profiles()
            return True
        return False

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        return self._profiles.get(profile_id)
