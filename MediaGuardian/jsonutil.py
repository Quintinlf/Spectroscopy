"""Tiny shared helper for reading/writing JSON state files atomically.

Used by both state.py (the processed-file ledger) and metrics.py (persisted
lifetime stats) so the "write to a temp file, then os.replace()" safety
pattern lives in exactly one place.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("media_guardian.jsonutil")


def read_json(path: Path, default: Any) -> Any:
    """Return the JSON contents of path, or `default` if missing/unreadable."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read %s (%s); using default.", path, exc)
        return default


def write_json_atomic(path: Path, data: Any) -> None:
    """Write data as JSON to path, atomically (temp file + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    except OSError as exc:
        logger.warning("Could not save %s: %s", path, exc)
        tmp_path.unlink(missing_ok=True)
