"""ffprobe-based metadata extraction for video files.

Runs a single `ffprobe ... -of json` call and parses the result into a
VideoMetadata dataclass used both for the console report and as input to the
compression decision engine (decision.py).
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("media_guardian.metadata")


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata for one video file, as reported by ffprobe."""

    duration_s: float
    width: int
    height: int
    fps: float
    video_codec: str
    bitrate_bps: int
    audio_codec: Optional[str]

    @property
    def bitrate_mbps(self) -> float:
        return self.bitrate_bps / 1_000_000


def _parse_frame_rate(raw: Optional[str]) -> float:
    """Parse an ffprobe frame-rate string like '60/1' or '30000/1001' into a float."""
    if not raw:
        return 0.0
    if "/" in raw:
        num_str, _, den_str = raw.partition("/")
        try:
            num, den = float(num_str), float(den_str)
            return num / den if den else 0.0
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def probe(path: Path) -> Optional[VideoMetadata]:
    """Return VideoMetadata for path, or None if it's not a valid/readable video."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_format", "-show_streams",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe timed out inspecting %s.", path.name)
        return None
    except OSError as exc:
        logger.warning("ffprobe could not run on %s: %s", path.name, exc)
        return None

    if result.returncode != 0 or not result.stdout.strip():
        logger.warning(
            "ffprobe reports %s is not a valid/readable video: %s",
            path.name, result.stderr.strip() or "no output",
        )
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse ffprobe output for %s: %s", path.name, exc)
        return None

    streams = payload.get("streams", [])
    fmt = payload.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        logger.warning("No video stream found in %s.", path.name)
        return None
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    def _to_int(value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    duration_s = _to_float(video_stream.get("duration") or fmt.get("duration"))
    fps = _parse_frame_rate(video_stream.get("avg_frame_rate")) or _parse_frame_rate(
        video_stream.get("r_frame_rate")
    )

    # Per-stream bitrate is frequently absent (notably in many MP4 containers);
    # fall back to the overall container bitrate reported in "format".
    bitrate_bps = _to_int(video_stream.get("bit_rate")) or _to_int(fmt.get("bit_rate"))

    return VideoMetadata(
        duration_s=duration_s,
        width=_to_int(video_stream.get("width")),
        height=_to_int(video_stream.get("height")),
        fps=fps,
        video_codec=(video_stream.get("codec_name") or "unknown").lower(),
        bitrate_bps=bitrate_bps,
        audio_codec=(audio_stream.get("codec_name").lower() if audio_stream and audio_stream.get("codec_name") else None),
    )
