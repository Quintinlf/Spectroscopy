"""Startup health dashboard: one glance at how Media Guardian is configured
and what it discovered, printed once when the program starts."""

from __future__ import annotations

import shutil
import subprocess
import sys

import config
from decision import DEFAULT_RULES
from processing import MediaProcessor
from reporting import SEPARATOR


def _ffmpeg_version() -> str:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        # "ffmpeg version 8.1.2-full_build-... Copyright ..." -> "8.1.2-full_build-..."
        parts = first_line.split()
        return parts[2] if len(parts) >= 3 else "unknown"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


def _disk_free_gb(path) -> float:
    try:
        return shutil.disk_usage(path).free / 1_000_000_000
    except OSError:
        return float("nan")


def print_startup_summary(processors: list[MediaProcessor], queue_size: int) -> None:
    lines = [
        SEPARATOR,
        "Media Guardian V2 - Startup Summary",
        SEPARATOR,
        f"Workers: {config.WORKER_COUNT}",
        f"Compression profile: {config.ACTIVE_PROFILE}",
        f"Watch folders: {config.WATCH_FOLDER}",
        f"Output folders: {config.OUTPUT_FOLDER}",
        f"Disk free: {_disk_free_gb(config.WATCH_FOLDER):.1f} GB",
        f"ffmpeg version: {_ffmpeg_version()}",
        f"Queue size: {queue_size}",
        f"Rules loaded: {len(DEFAULT_RULES)}",
        f"Processors loaded: {', '.join(p.name for p in processors) or 'none'}",
        SEPARATOR,
    ]
    print("\n".join(lines))
    sys.stdout.flush()  # console output must be visible immediately even when stdout is piped/redirected
