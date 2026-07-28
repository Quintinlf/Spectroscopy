"""Automatic folder organization for processed files.

Generic by design: it only knows "move/copy this file into
ORGANIZE_BASE_FOLDER/<category>", where `category` is a path-like hint
supplied by whichever MediaProcessor produced the ProcessingResult (e.g.
"Videos/HEVC", "Videos/Shorts"). A future ImageProcessor could just as
easily hint "Photos/Screenshots" -- this module never hardcodes video
categories itself.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("media_guardian.organizer")


def _unique_path(target_dir: Path, filename: str) -> Path:
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    n = 1
    while True:
        candidate = target_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def organize(file_path: Path, category: Optional[str]) -> Optional[Path]:
    """Move or copy file_path into config.ORGANIZE_BASE_FOLDER/<category>.

    Returns the new path on success, or None if organization was skipped
    (disabled, no category, or an error occurred -- in which case file_path
    is left exactly where it was).
    """
    if not config.ORGANIZE_ENABLED or not category:
        return None

    target_dir = config.ORGANIZE_BASE_FOLDER / category
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = _unique_path(target_dir, file_path.name)
        if config.ORGANIZE_MODE == "copy":
            shutil.copy2(file_path, target_path)
        else:
            shutil.move(str(file_path), str(target_path))
    except OSError as exc:
        logger.warning("Could not organize %s into %s: %s", file_path.name, category, exc)
        return None

    logger.info("Organized %s -> %s", file_path.name, target_path)
    return target_path
