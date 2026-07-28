"""Generalized per-file pipeline: ledger dedup -> find processor -> analyze
-> submit to the job queue -> (later, async) organize/thumbnail/record.

This is the processor-agnostic replacement for what used to be
media_watcher.process_new_video(). media_watcher.py now only does
filesystem/watchdog plumbing and calls Pipeline.process_new_file(); nothing
here knows what a "video" is -- that's entirely encapsulated in whichever
MediaProcessor.supports() claims the file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import organizer
import reporting
import state
from job_queue import Job, JobQueue
from metrics import PerformanceMetrics
from processing import MediaProcessor, ProcessingResult
from summary import run_summary

logger = logging.getLogger("media_guardian.pipeline")


class Pipeline:
    """Wires processors + ledger + job queue + reporting + organizer +
    metrics together, with no knowledge of any specific media type."""

    def __init__(
        self,
        processors: list[MediaProcessor],
        metrics: PerformanceMetrics,
        ledger: state.ProcessedLedger,
    ):
        self._processors = processors
        self._metrics = metrics
        self._ledger = ledger
        self._job_queue: Optional[JobQueue] = None  # attached after construction, see attach_job_queue

    def attach_job_queue(self, job_queue: JobQueue) -> None:
        self._job_queue = job_queue

    def find_processor(self, path: Path) -> Union[MediaProcessor, None]:
        for processor in self._processors:
            try:
                if processor.supports(path):
                    return processor
            except Exception:
                logger.exception("Processor %s raised while checking support for %s.", processor.name, path.name)
        return None

    def process_new_file(self, path: Path) -> None:
        """Handle one candidate file end-to-end: dedup, find processor,
        analyze, and (if warranted) enqueue for processing.

        Every exception is caught here so one bad file can never take down
        the watcher thread that called this.
        """
        try:
            self._process_new_file_inner(path)
        except Exception:
            logger.exception("Unexpected error while handling %s.", path.name)
            run_summary.record_error()

    def _process_new_file_inner(self, path: Path) -> None:
        try:
            stat = path.stat()
        except FileNotFoundError:
            logger.warning("Skipping %s: file disappeared before it could be handled.", path.name)
            return

        size_bytes = stat.st_size
        ledger_key = state.make_key(path, size_bytes, stat.st_mtime_ns)
        if self._ledger.seen(ledger_key):
            logger.info("Skipping %s: already processed (unchanged since last run).", path.name)
            return

        processor = self.find_processor(path)
        if processor is None:
            logger.debug("No processor supports %s; ignoring.", path.name)
            return

        metadata = processor.extract_metadata(path)
        if metadata is None:
            logger.warning("Skipping %s: %s processor could not read this file.", path.name, processor.name)
            return  # not marked in the ledger -- worth revisiting if the file is later fixed

        decision = processor.analyze(metadata, path, size_bytes)
        reporting.print_detection_report(path.name, processor.describe_metadata(metadata), size_bytes, decision)

        if not decision.should_process:
            logger.info("Skip: %s (%s)", path.name, decision.reason_text)
            reporting.print_skip_footer()
            run_summary.record_skipped()
            self._ledger.mark(ledger_key, "skipped", {"reason": decision.reason_text})
            return

        if self._job_queue is None:
            raise RuntimeError("Pipeline.attach_job_queue() must be called before processing files.")

        logger.info("Processing queued: %s (%s)", path.name, decision.reason_text)
        job = Job(file_path=path, processor=processor, decision=decision, ledger_key=ledger_key)
        self._job_queue.submit(job)

    def handle_job_result(self, job: Job, outcome: Union[ProcessingResult, BaseException]) -> None:
        """JobQueue.on_result callback: runs once a queued job finishes.

        Not marking the ledger on any failure path is deliberate -- an
        unmarked file is automatically retried on the next run.
        """
        if isinstance(outcome, BaseException):
            reporting.print_error_footer(str(outcome))
            run_summary.record_error()
            return

        result = outcome
        if not result.success:
            reporting.print_error_footer(result.error or "unknown error")
            logger.error("Processing failed for %s: %s", job.file_path.name, result.error)
            run_summary.record_error()
            return

        final_path = result.output_path
        if final_path is not None and result.category:
            organized_path = organizer.organize(final_path, result.category)
            if organized_path is not None:
                final_path = organized_path

        if final_path is not None:
            thumbnail_path = job.processor.generate_thumbnail(final_path)
            if thumbnail_path is not None:
                logger.info("Thumbnail ready: %s", thumbnail_path)

        new_size = result.new_size if result.new_size is not None else result.original_size
        bytes_saved = result.original_size - new_size
        reporting.print_compression_result(result.original_size, new_size)
        logger.info(
            "Done: %s (elapsed=%.1fs, saved=%d bytes) -> %s",
            job.file_path.name, result.elapsed_seconds, bytes_saved, final_path,
        )

        run_summary.record_processed(bytes_saved)
        self._metrics.record_job(result)
        self._ledger.mark(job.ledger_key, "processed", {"output": str(final_path) if final_path else None})
