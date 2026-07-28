"""Persistent ledger of already-handled files so nothing is ever processed twice.

The in-memory `_in_progress` guard in media_watcher.py only protects against
double-processing *within a single run*. Without a persistent record, simply
restarting Media Guardian would rediscover every file still sitting in
incoming_media/ and reprocess (and potentially recompress) all of them. This
module closes that gap with a small JSON ledger keyed by file identity.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import config
from jsonutil import read_json, write_json_atomic


def make_key(path: Path, size_bytes: int, mtime_ns: int) -> str:
    """Build a ledger key from file identity (path + size + mtime).

    Including size and mtime means a file that gets edited/replaced with the
    same name is correctly treated as new content, not a duplicate.
    """
    return f"{path.resolve()}:{size_bytes}:{mtime_ns}"


class ProcessedLedger:
    """Thread-safe, disk-backed record of files Media Guardian has handled."""

    def __init__(self, ledger_path: Path):
        self._path = ledger_path
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        self._entries = read_json(self._path, default={})

    def _save_locked(self) -> None:
        """Write the ledger atomically. Caller must hold self._lock."""
        write_json_atomic(self._path, self._entries)

    def seen(self, key: str) -> bool:
        with self._lock:
            return key in self._entries

    def mark(self, key: str, outcome: str, extra: Optional[dict] = None) -> None:
        """Record a successfully-handled file. `outcome` is e.g. 'compressed' or 'skipped'."""
        record = {"outcome": outcome}
        if extra:
            record.update(extra)
        with self._lock:
            self._entries[key] = record
            self._save_locked()


_default_ledger: Optional[ProcessedLedger] = None
_default_ledger_lock = threading.Lock()


def get_default_ledger() -> ProcessedLedger:
    """Return a process-wide singleton ledger backed by config.PROCESSED_LEDGER_FILE."""
    global _default_ledger
    with _default_ledger_lock:
        if _default_ledger is None:
            _default_ledger = ProcessedLedger(config.PROCESSED_LEDGER_FILE)
        return _default_ledger
