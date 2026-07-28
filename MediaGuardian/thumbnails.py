"""ffmpeg-based thumbnail generation for video files.

No new dependency: reuses the ffmpeg binary already required by
video_optimizer.py. Kept generic to "a video file in, an image file out" so
any future video-ish processor could reuse it.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("media_guardian.thumbnails")


def generate_thumbnail(video_path: Path) -> Optional[Path]:
    """Generate a thumbnail for video_path, or return the existing one.

    Returns the thumbnail path on success (including when it already
    existed and generation was skipped), or None on failure.
    """
    config.THUMBNAIL_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    output_path = config.THUMBNAIL_OUTPUT_FOLDER / f"{video_path.stem}.{config.THUMBNAIL_FORMAT}"

    if output_path.exists():
        logger.debug("Thumbnail already exists for %s, skipping.", video_path.name)
        return output_path

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(config.THUMBNAIL_TIMESTAMP_SECONDS),
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", f"scale={config.THUMBNAIL_WIDTH}:-1",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        logger.warning("Thumbnail generation timed out for %s.", video_path.name)
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not generate thumbnail for %s: %s", video_path.name, exc)
        return None

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        logger.warning(
            "Thumbnail generation failed for %s: %s",
            video_path.name, result.stderr.strip()[-400:],
        )
        output_path.unlink(missing_ok=True)
        return None

    return output_path
