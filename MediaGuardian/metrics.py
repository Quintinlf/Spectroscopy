"""Performance metrics: this-run rate tracking plus persisted lifetime stats.

Deliberately separate from summary.py: summary.py is an in-memory tally that
resets every run ("what did this run do"), while this module answers
"how is Media Guardian doing overall" and survives restarts.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import config
import reporting
from jsonutil import read_json, write_json_atomic
from processing import ProcessingResult


@dataclass
class _LifetimeStats:
    files_processed: int = 0
    total_original_bytes: int = 0
    total_new_bytes: int = 0
    total_bytes_saved: int = 0
    total_encode_seconds: float = 0.0
    total_original_bitrate_mbps: float = 0.0
    total_new_bitrate_mbps: float = 0.0
    bitrate_sample_count: int = 0
    today_date: str = ""
    today_bytes_saved: int = 0


class PerformanceMetrics:
    """Thread-safe, disk-backed performance tracker."""

    def __init__(self, path: Path, rate_window_seconds: float):
        self._path = path
        self._rate_window_seconds = rate_window_seconds
        self._lock = threading.Lock()
        self._recent_completions: deque[float] = deque()
        self._stats = self._load()
        self._roll_day_if_needed_locked()

    def _load(self) -> _LifetimeStats:
        data = read_json(self._path, default=None)
        if not isinstance(data, dict):
            return _LifetimeStats()
        known_fields = _LifetimeStats.__dataclass_fields__.keys()
        return _LifetimeStats(**{k: v for k, v in data.items() if k in known_fields})

    def _save_locked(self) -> None:
        write_json_atomic(self._path, asdict(self._stats))

    def _roll_day_if_needed_locked(self) -> None:
        today = date.today().isoformat()
        if self._stats.today_date != today:
            self._stats.today_date = today
            self._stats.today_bytes_saved = 0

    def record_job(self, result: ProcessingResult) -> None:
        """Record one successfully completed job's contribution to the stats."""
        if not result.success or result.new_size is None:
            return

        bytes_saved = max(0, result.original_size - result.new_size)
        original_bitrate = result.extra.get("original_bitrate_mbps")
        new_bitrate = result.extra.get("new_bitrate_mbps")

        with self._lock:
            self._roll_day_if_needed_locked()
            s = self._stats
            s.files_processed += 1
            s.total_original_bytes += result.original_size
            s.total_new_bytes += result.new_size
            s.total_bytes_saved += bytes_saved
            s.total_encode_seconds += result.elapsed_seconds
            s.today_bytes_saved += bytes_saved
            if original_bitrate is not None and new_bitrate is not None:
                s.total_original_bitrate_mbps += original_bitrate
                s.total_new_bitrate_mbps += new_bitrate
                s.bitrate_sample_count += 1
            self._recent_completions.append(time.time())
            self._save_locked()

    def _files_per_hour_locked(self) -> float:
        cutoff = time.time() - self._rate_window_seconds
        while self._recent_completions and self._recent_completions[0] < cutoff:
            self._recent_completions.popleft()
        window_hours = self._rate_window_seconds / 3600
        return len(self._recent_completions) / window_hours if window_hours else 0.0

    def render(self) -> str:
        with self._lock:
            self._roll_day_if_needed_locked()
            s = self._stats
            files_per_hour = self._files_per_hour_locked()

            compression_ratio: Optional[float] = None
            if s.total_original_bytes:
                compression_ratio = s.total_new_bytes / s.total_original_bytes

            avg_encode_seconds = (s.total_encode_seconds / s.files_processed) if s.files_processed else 0.0

            avg_bitrate_reduction_pct: Optional[float] = None
            if s.bitrate_sample_count:
                avg_original = s.total_original_bitrate_mbps / s.bitrate_sample_count
                avg_new = s.total_new_bitrate_mbps / s.bitrate_sample_count
                if avg_original:
                    avg_bitrate_reduction_pct = (1 - avg_new / avg_original) * 100

            today_saved, lifetime_saved = s.today_bytes_saved, s.total_bytes_saved

        lines = [
            "Performance Metrics (lifetime)",
            "-" * 50,
            f"Files/hour:                {files_per_hour:.1f}",
            f"Compression ratio:         {compression_ratio:.0%}" if compression_ratio is not None else "Compression ratio:         n/a",
            f"Average encode time:       {avg_encode_seconds:.1f}s",
            (
                f"Average bitrate reduction: {avg_bitrate_reduction_pct:.0f}%"
                if avg_bitrate_reduction_pct is not None
                else "Average bitrate reduction: n/a"
            ),
            f"Disk saved today:          {reporting.format_size(today_saved)}",
            f"Disk saved lifetime:       {reporting.format_size(lifetime_saved)}",
            "-" * 50,
        ]
        return "\n".join(lines)


_default_metrics: Optional[PerformanceMetrics] = None
_default_metrics_lock = threading.Lock()


def get_default_metrics() -> PerformanceMetrics:
    """Return a process-wide singleton backed by config.METRICS_FILE."""
    global _default_metrics
    with _default_metrics_lock:
        if _default_metrics is None:
            _default_metrics = PerformanceMetrics(config.METRICS_FILE, config.METRICS_RATE_WINDOW_SECONDS)
        return _default_metrics
