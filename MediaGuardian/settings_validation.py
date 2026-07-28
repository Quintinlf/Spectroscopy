"""Startup validation for config.py.

Runs before anything else (ffmpeg checks, watcher, job queue) so a typo'd
config value produces one clear, human-readable error list instead of a
confusing failure deep inside a worker thread later.
"""

from __future__ import annotations

from pathlib import Path

import compression_profiles
import config


class ConfigError(Exception):
    """Raised with a human-readable, bulleted list of every problem found."""


def _check_positive_number(errors: list[str], name: str, value) -> None:
    if not isinstance(value, (int, float)) or value <= 0:
        errors.append(f"config.{name} must be a positive number (got {value!r})")


def _check_positive_int(errors: list[str], name: str, value) -> None:
    if not isinstance(value, int) or value <= 0:
        errors.append(f"config.{name} must be a positive integer (got {value!r})")


def _check_folder_creatable(errors: list[str], name: str, value) -> None:
    path = Path(value)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        errors.append(f"config.{name} ({path}) is not a usable folder: {exc}")


def _check_choice(errors: list[str], name: str, value, choices: set) -> None:
    if value not in choices:
        errors.append(f"config.{name} must be one of {sorted(choices)} (got {value!r})")


def validate_config() -> None:
    """Raise ConfigError listing every invalid setting found, or return None."""
    errors: list[str] = []

    if config.ACTIVE_PROFILE not in compression_profiles.PROFILES:
        errors.append(
            f"config.ACTIVE_PROFILE={config.ACTIVE_PROFILE!r} is not defined in "
            f"compression_profiles.PROFILES (available: {sorted(compression_profiles.PROFILES)})"
        )

    _check_positive_int(errors, "WORKER_COUNT", config.WORKER_COUNT)
    _check_positive_int(errors, "JOB_QUEUE_MAX_SIZE", config.JOB_QUEUE_MAX_SIZE)

    _check_positive_number(errors, "MAX_SIZE_MB", config.MAX_SIZE_MB)
    _check_positive_number(errors, "MAX_VIDEO_BITRATE_MBPS", config.MAX_VIDEO_BITRATE_MBPS)
    _check_positive_number(errors, "TARGET_BITRATE_MBPS", config.TARGET_BITRATE_MBPS)
    _check_positive_int(errors, "MAX_RESOLUTION_WIDTH", config.MAX_RESOLUTION_WIDTH)
    _check_positive_int(errors, "MAX_RESOLUTION_HEIGHT", config.MAX_RESOLUTION_HEIGHT)
    _check_positive_number(errors, "SHORTS_MAX_DURATION_SECONDS", config.SHORTS_MAX_DURATION_SECONDS)

    if config.THUMBNAIL_ENABLED:
        _check_positive_number(errors, "THUMBNAIL_TIMESTAMP_SECONDS", config.THUMBNAIL_TIMESTAMP_SECONDS)
        _check_positive_int(errors, "THUMBNAIL_WIDTH", config.THUMBNAIL_WIDTH)
        _check_choice(errors, "THUMBNAIL_FORMAT", config.THUMBNAIL_FORMAT, {"jpg", "webp"})
        _check_folder_creatable(errors, "THUMBNAIL_OUTPUT_FOLDER", config.THUMBNAIL_OUTPUT_FOLDER)

    if config.ORGANIZE_ENABLED:
        _check_choice(errors, "ORGANIZE_MODE", config.ORGANIZE_MODE, {"move", "copy"})
        _check_folder_creatable(errors, "ORGANIZE_BASE_FOLDER", config.ORGANIZE_BASE_FOLDER)

    _check_folder_creatable(errors, "WATCH_FOLDER", config.WATCH_FOLDER)
    _check_folder_creatable(errors, "OUTPUT_FOLDER", config.OUTPUT_FOLDER)
    _check_folder_creatable(errors, "STATE_DIR", config.STATE_DIR)

    if not config.VIDEO_EXTENSIONS:
        errors.append("config.VIDEO_EXTENSIONS must not be empty")

    if errors:
        bullet_list = "\n".join(f"  - {e}" for e in errors)
        raise ConfigError(f"Invalid configuration ({len(errors)} problem(s) found):\n{bullet_list}")
