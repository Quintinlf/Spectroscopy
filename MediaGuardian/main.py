"""Entry point for Media Guardian: an extensible, plugin-based media
automation platform. Watches a folder and, for every file, hands it to
whichever auto-discovered MediaProcessor claims it (video today; images,
audio, gifs, PDFs, ... in the future -- no changes needed here for those).
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import time

import config
import dashboard
import media_watcher
import plugins
import settings_validation
import state
import video_optimizer
from job_queue import JobQueue
from metrics import get_default_metrics
from pipeline import Pipeline
from summary import run_summary

logger = logging.getLogger("media_guardian")


def _setup_logging() -> None:
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [console_handler]
    try:
        config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except OSError as exc:
        # Logging to console must never be blocked by a file-logging failure
        # (e.g. read-only filesystem, permissions issue).
        print(f"Warning: could not set up file logging at {config.LOG_FILE}: {exc}", file=sys.stderr)

    logging.basicConfig(level=level, handlers=handlers)


def main() -> int:
    _setup_logging()

    try:
        settings_validation.validate_config()
    except settings_validation.ConfigError as exc:
        logger.error(str(exc))
        return 1

    try:
        video_optimizer.check_ffmpeg_available()
    except video_optimizer.FFmpegNotFoundError as exc:
        logger.error(str(exc))
        return 1

    config.WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    processors = plugins.discover_processors()
    if not processors:
        logger.error("No media processors were discovered; nothing to do.")
        return 1

    ledger = state.get_default_ledger()
    metrics = get_default_metrics()

    pipeline = Pipeline(processors=processors, metrics=metrics, ledger=ledger)
    job_queue = JobQueue(
        worker_count=config.WORKER_COUNT,
        max_queue_size=config.JOB_QUEUE_MAX_SIZE,
        on_result=pipeline.handle_job_result,
    )
    pipeline.attach_job_queue(job_queue)
    job_queue.start()

    dashboard.print_startup_summary(processors, queue_size=config.JOB_QUEUE_MAX_SIZE)

    observer = media_watcher.start_watching(pipeline)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping (Ctrl+C received)...")
    finally:
        observer.stop()
        observer.join()
        job_queue.shutdown(wait=True)
        print("\n" + run_summary.render())
        print("\n" + metrics.render())
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
