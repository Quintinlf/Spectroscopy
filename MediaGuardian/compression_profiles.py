"""Named encode presets for ffmpeg, selected by config.ACTIVE_PROFILE.

Adding a new profile (or retuning an existing one) is a config-only change:
edit PROFILES below and/or flip config.ACTIVE_PROFILE. Nothing else in the
codebase needs to change to pick a different encode target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import config


@dataclass(frozen=True)
class CompressionProfile:
    """One complete set of ffmpeg encode settings."""

    name: str
    codec: str
    crf: int
    preset: str
    audio_bitrate: str
    # Optional hard cap for this profile, independent of the decision
    # engine's own per-file downscale logic (see decision.py). Useful for a
    # profile like SHARE that should always stay small regardless of the
    # source resolution.
    max_resolution_height: Optional[int] = None


PROFILES: dict[str, CompressionProfile] = {
    "ARCHIVE": CompressionProfile(
        name="ARCHIVE",
        codec="libx265",
        crf=18,
        preset="slow",
        audio_bitrate="192k",
    ),
    "BALANCED": CompressionProfile(
        name="BALANCED",
        codec="libx265",
        crf=26,
        preset="medium",
        audio_bitrate="128k",
    ),
    "SHARE": CompressionProfile(
        name="SHARE",
        codec="libx264",
        crf=28,
        preset="fast",
        audio_bitrate="96k",
        max_resolution_height=720,
    ),
    "HIGH_QUALITY": CompressionProfile(
        name="HIGH_QUALITY",
        codec="libx265",
        crf=20,
        preset="slow",
        audio_bitrate="192k",
    ),
}


class UnknownProfileError(ValueError):
    """Raised when config.ACTIVE_PROFILE doesn't match a defined profile."""


def get_active_profile() -> CompressionProfile:
    """Return the CompressionProfile selected by config.ACTIVE_PROFILE."""
    try:
        return PROFILES[config.ACTIVE_PROFILE]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise UnknownProfileError(
            f"config.ACTIVE_PROFILE={config.ACTIVE_PROFILE!r} is not a known "
            f"profile. Available profiles: {available}."
        ) from exc
