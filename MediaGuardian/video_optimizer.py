"""ffmpeg wrapper for compressing video files.

Metadata inspection lives in metadata.py; the compression decision lives in
decision.py. This module's only job is to turn a (input path, downscale
hint, active profile) combination into a safe, hardened ffmpeg invocation.

Deliberately takes a plain `downscale_height` rather than a whole
CompressionDecision: decision.py's rule-engine output is video-specific and
now lives one layer up, behind the generic MediaProcessor contract in
processing.py (see processors/video_processor.py) -- this module stays a
plain ffmpeg wrapper with no knowledge of how that number was decided.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import compression_profiles
import config

logger = logging.getLogger("media_guardian.video_optimizer")


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg or ffprobe is not available on PATH."""


def check_ffmpeg_available() -> None:
    """Raise FFmpegNotFoundError if ffmpeg/ffprobe aren't on PATH."""
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise FFmpegNotFoundError(
            f"Required tool(s) not found on PATH: {', '.join(missing)}. "
            "Install ffmpeg (which bundles ffprobe) and try again."
        )


def _unique_output_path(output_dir: Path, filename: str) -> Path:
    """Return a non-colliding path in output_dir, appending _1, _2, ... on collision."""
    candidate = output_dir / filename
    if not candidate.exists():
        return candidate

    stem, suffix = candidate.stem, candidate.suffix
    n = 1
    while True:
        candidate = output_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _resolve_target_height(downscale_height: Optional[int], profile: compression_profiles.CompressionProfile) -> Optional[int]:
    """Combine the caller's per-file downscale hint with the profile's own
    cap (e.g. SHARE always caps at 720p), taking the smaller of the two."""
    candidates = [h for h in (downscale_height, profile.max_resolution_height) if h is not None]
    return min(candidates) if candidates else None


def compress_video(input_path: Path, downscale_height: Optional[int] = None) -> Optional[Path]:
    """Compress input_path into config.OUTPUT_FOLDER using the active profile.

    `downscale_height`, if given, is combined with the active profile's own
    resolution cap (whichever is smaller wins).

    Returns the final output path on success, or None on failure. The original
    file is never modified or deleted. Compresses to a .partial temp file first
    so an interrupted run never leaves a corrupt file at the final output path.
    """
    config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    output_path = _unique_output_path(config.OUTPUT_FOLDER, input_path.name)
    tmp_output = output_path.with_name(output_path.stem + ".partial" + output_path.suffix)

    profile = compression_profiles.get_active_profile()
    target_height = _resolve_target_height(downscale_height, profile)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-map_metadata", "0",
        "-c:v", profile.codec,
        "-crf", str(profile.crf),
        "-preset", profile.preset,
    ]
    if target_height is not None:
        cmd += ["-vf", f"scale=-2:{target_height}"]
    cmd += [
        "-c:a", "aac",
        "-b:a", profile.audio_bitrate,
        "-movflags", "+faststart",
        str(tmp_output),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=config.FFMPEG_TIMEOUT_SECONDS,
        )
    except KeyboardInterrupt:
        logger.error("Compression interrupted for %s; cleaning up partial output.", input_path.name)
        tmp_output.unlink(missing_ok=True)
        raise
    except subprocess.TimeoutExpired:
        logger.error(
            "ffmpeg timed out after %ss on %s; killing and cleaning up.",
            config.FFMPEG_TIMEOUT_SECONDS, input_path.name,
        )
        tmp_output.unlink(missing_ok=True)
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("Could not launch/run ffmpeg for %s: %s", input_path.name, exc)
        tmp_output.unlink(missing_ok=True)
        return None

    if result.returncode != 0:
        logger.error(
            "ffmpeg failed on %s (exit %s): %s",
            input_path.name, result.returncode, result.stderr.strip()[-800:],
        )
        tmp_output.unlink(missing_ok=True)
        return None

    if not tmp_output.exists():
        logger.error("ffmpeg reported success for %s but produced no output file.", input_path.name)
        return None

    try:
        tmp_output.rename(output_path)
    except OSError as exc:
        logger.error("Could not finalize output for %s: %s", input_path.name, exc)
        tmp_output.unlink(missing_ok=True)
        return None

    return output_path
