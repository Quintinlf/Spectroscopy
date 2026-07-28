"""In-memory summary of what Media Guardian has done during this run.

Purely in-memory (resets on restart) by design -- the persistent record of
what was done to which file lives in state.py's ledger; this module is just
a running tally for human-readable status output.
"""

from __future__ import annotations

import threading


def _format_bytes(num_bytes: float) -> str:
    if num_bytes >= 1024 ** 3:
        return f"{num_bytes / 1024 ** 3:.2f} GB"
    return f"{num_bytes / 1024 ** 2:.1f} MB"


class RunSummary:
    """Thread-safe counters tracking this run's activity."""

    def __init__(self):
        self._lock = threading.Lock()
        self.files_processed = 0
        self.files_skipped = 0
        self.files_errored = 0
        self.bytes_saved = 0

    def record_processed(self, bytes_saved: int) -> None:
        with self._lock:
            self.files_processed += 1
            self.bytes_saved += max(0, bytes_saved)

    def record_skipped(self) -> None:
        with self._lock:
            self.files_skipped += 1

    def record_error(self) -> None:
        with self._lock:
            self.files_errored += 1

    def render(self) -> str:
        with self._lock:
            processed, skipped, errored, saved = (
                self.files_processed, self.files_skipped, self.files_errored, self.bytes_saved,
            )
        lines = [
            "Summary",
            "-" * 50,
            f"Files processed: {processed}",
            f"Files skipped:   {skipped}",
            f"Space saved:     {_format_bytes(saved)}",
            f"Errors:          {errored}",
            "-" * 50,
        ]
        return "\n".join(lines)


run_summary = RunSummary()
