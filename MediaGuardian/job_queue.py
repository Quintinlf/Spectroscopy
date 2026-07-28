"""A small bounded worker pool so Media Guardian never launches an unbounded
number of ffmpeg (or other processor) subprocesses at once.

Design:
    - `Job.processor`/`Job.decision` carry everything a worker needs; the
      queue itself has zero video-specific knowledge.
    - `submit()` blocks (with a log warning) once the queue is full --
      natural backpressure instead of dropping work or spawning more workers
      than configured.
    - A failing job is caught *inside* the worker loop, so one bad job can
      never kill a worker thread or stop the queue from processing the rest.
    - `shutdown()` is graceful: it stops workers from picking up *new* queued
      jobs, but lets whichever job each worker is already running finish.
      Anything still sitting in the queue is abandoned (logged) -- since
      it was never marked in the processed-file ledger, it's automatically
      retried the next time Media Guardian starts.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Union

from processing import MediaProcessor, ProcessingDecision, ProcessingResult

logger = logging.getLogger("media_guardian.job_queue")

OnResult = Callable[["Job", Union[ProcessingResult, BaseException]], None]


@dataclass
class Job:
    file_path: Path
    processor: MediaProcessor
    decision: ProcessingDecision
    # Opaque bookkeeping key the caller (pipeline.py) uses to mark the
    # processed-file ledger once the job completes. The queue itself never
    # inspects it.
    ledger_key: str = ""
    submitted_at: float = field(default_factory=time.time)


class JobQueue:
    """Bounded producer/consumer queue with a fixed-size worker pool."""

    def __init__(self, worker_count: int, max_queue_size: int, on_result: OnResult):
        self._queue: "queue.Queue[Job]" = queue.Queue(maxsize=max_queue_size)
        self._worker_count = worker_count
        self._on_result = on_result
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        """Spawn the worker pool. Safe to call once."""
        for i in range(self._worker_count):
            thread = threading.Thread(target=self._worker_loop, name=f"jobqueue-worker-{i}", daemon=False)
            thread.start()
            self._threads.append(thread)
        logger.info(
            "Job queue started: %d worker(s), max queue size %d.",
            self._worker_count, self._queue.maxsize,
        )

    def submit(self, job: Job) -> bool:
        """Enqueue a job, blocking (with a log message) if the queue is full.

        Returns False (without enqueuing) if shutdown has already begun.
        """
        if self._stop_event.is_set():
            logger.warning("Job queue is shutting down; refusing new job for %s.", job.file_path.name)
            return False

        if self._queue.full():
            logger.warning(
                "Job queue is full (max %d); waiting for a worker to free up before submitting %s.",
                self._queue.maxsize, job.file_path.name,
            )

        self._queue.put(job)
        logger.info("Job queued: %s (queue depth=%d)", job.file_path.name, self._queue.qsize())
        return True

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._run_job(job)
            finally:
                self._queue.task_done()

    def _run_job(self, job: Job) -> None:
        started = time.monotonic()
        logger.info("Job started: %s (queue depth=%d)", job.file_path.name, self._queue.qsize())
        try:
            result: Union[ProcessingResult, BaseException] = job.processor.process(job.file_path, job.decision)
        except Exception as exc:  # noqa: BLE001 -- isolate failures so the worker loop keeps running
            logger.exception("Job failed: %s", job.file_path.name)
            result = exc
        else:
            elapsed = time.monotonic() - started
            logger.info(
                "Job finished: %s (elapsed=%.1fs, queue depth=%d)",
                job.file_path.name, elapsed, self._queue.qsize(),
            )

        try:
            self._on_result(job, result)
        except Exception:
            logger.exception("on_result callback raised while handling %s; ignoring.", job.file_path.name)

    def shutdown(self, wait: bool = True) -> None:
        """Stop accepting/starting new jobs. Jobs already running are allowed
        to finish; anything still queued is abandoned and logged."""
        self._stop_event.set()
        abandoned = self._queue.qsize()
        if abandoned:
            logger.warning(
                "Shutting down job queue with %d job(s) still queued; they were never "
                "marked as processed, so they'll be retried on the next run.",
                abandoned,
            )
        if wait:
            for thread in self._threads:
                thread.join()
        logger.info("Job queue stopped.")
