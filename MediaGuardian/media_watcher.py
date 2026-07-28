"""Filesystem watching only.

Deliberately has zero knowledge of "video" or any other media type: it
filters out temp/partial files, waits for a file to finish being written,
guards against duplicate concurrent handling of the same path, and then
hands off to pipeline.Pipeline.process_new_file(). What happens to that file
from there on is entirely up to whichever MediaProcessor claims it.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config
from pipeline import Pipeline

logger = logging.getLogger("media_guardian.watcher")


def _is_ignored(path: Path) -> bool:
    """True if this filename looks like a temp/partial/editor-swap file."""
    name = path.name
    if any(name.startswith(prefix) for prefix in config.IGNORED_NAME_PREFIXES):
        return True
    if any(name.endswith(suffix) for suffix in config.IGNORED_SUFFIXES):
        return True
    return False


def _is_stable(path: Path) -> bool:
    """Poll a file's size until it stops changing, indicating the copy/write finished.

    Returns False if the file disappears or never stabilizes within a bounded
    number of checks (so a file that's copying forever doesn't hang a worker thread).
    """
    last_size = -1
    stable_cycles = 0
    max_checks = config.STABLE_REQUIRED_CYCLES * 30

    for _ in range(max_checks):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False

        if size == last_size:
            stable_cycles += 1
            if stable_cycles >= config.STABLE_REQUIRED_CYCLES:
                return True
        else:
            stable_cycles = 0
            last_size = size

        time.sleep(config.STABLE_POLL_SECONDS)

    logger.warning("Gave up waiting for %s to finish copying.", path.name)
    return False


class MediaGuardianHandler(FileSystemEventHandler):
    """Watches for new files and hands each to the pipeline in its own
    background thread (one thread per file, not per compression -- the
    expensive work is bounded by the job queue's worker pool, not by this)."""

    def __init__(self, pipeline: Pipeline):
        super().__init__()
        self._pipeline = pipeline
        self._lock = threading.Lock()
        self._in_progress: set[str] = set()

    def _maybe_handle(self, path_str: str) -> None:
        path = Path(path_str)
        if _is_ignored(path):
            return

        with self._lock:
            if path_str in self._in_progress:
                return
            self._in_progress.add(path_str)

        def _run():
            try:
                if _is_stable(path):
                    self._pipeline.process_new_file(path)
                else:
                    logger.warning("Skipping %s: file disappeared or never finished copying.", path.name)
            finally:
                with self._lock:
                    self._in_progress.discard(path_str)

        threading.Thread(target=_run, daemon=True).start()

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_handle(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._maybe_handle(event.dest_path)


def start_watching(pipeline: Pipeline) -> Observer:
    """Create, start, and return an Observer watching config.WATCH_FOLDER."""
    config.WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    handler = MediaGuardianHandler(pipeline)
    observer = Observer()
    observer.schedule(handler, str(config.WATCH_FOLDER), recursive=False)
    observer.start()
    logger.info("Watching %s for new files...", config.WATCH_FOLDER)
    return observer
