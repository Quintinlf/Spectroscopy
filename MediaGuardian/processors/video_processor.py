"""Video processor: the V1 pipeline (ffprobe metadata -> rule engine ->
ffmpeg compression) adapted to the generic MediaProcessor contract.

This module is intentionally a thin adapter -- all the actual logic still
lives in metadata.py, decision.py, compression_profiles.py, and
video_optimizer.py, unchanged from V1.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

import compression_profiles
import config
import metadata as metadata_module
import reporting
import thumbnails
import video_optimizer
from decision import DEFAULT_ENGINE, RuleContext
from metadata import VideoMetadata
from processing import MediaProcessor, ProcessingDecision, ProcessingResult

logger = logging.getLogger("media_guardian.processors.video")

_HEVC_PROFILE_CODECS = {"libx265"}
_H264_PROFILE_CODECS = {"libx264"}


class VideoProcessor(MediaProcessor):
    """Handles video files: analyze via ffprobe + the compression rule
    engine, then compress via ffmpeg."""

    name = "video"

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in config.VIDEO_EXTENSIONS

    def extract_metadata(self, file_path: Path) -> Optional[VideoMetadata]:
        return metadata_module.probe(file_path)

    def analyze(self, metadata: Any, file_path: Path, size_bytes: int) -> ProcessingDecision:
        video_meta: VideoMetadata = metadata
        ctx = RuleContext(metadata=video_meta, size_bytes=size_bytes)
        result = DEFAULT_ENGINE.evaluate(ctx)
        return ProcessingDecision(
            should_process=result.compress,
            reasons=result.reasons,
            estimated_savings=result.estimated_savings,
            extra={"downscale_height": result.downscale_height, "metadata": video_meta},
        )

    def process(self, file_path: Path, decision: ProcessingDecision) -> ProcessingResult:
        original_size = file_path.stat().st_size
        downscale_height = decision.extra.get("downscale_height")

        started_at = time.monotonic()
        try:
            output_path = video_optimizer.compress_video(file_path, downscale_height=downscale_height)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 -- isolate any unexpected ffmpeg-wrapper failure
            logger.exception("Unexpected error compressing %s.", file_path.name)
            return ProcessingResult(
                success=False, original_size=original_size, error=str(exc),
                elapsed_seconds=time.monotonic() - started_at,
            )
        elapsed = time.monotonic() - started_at

        if output_path is None:
            return ProcessingResult(
                success=False, original_size=original_size,
                error="ffmpeg did not produce output, see logs", elapsed_seconds=elapsed,
            )

        new_size = output_path.stat().st_size
        video_meta: Optional[VideoMetadata] = decision.extra.get("metadata")
        category = self._categorize(video_meta)
        extra = self._bitrate_extra(video_meta, new_size)
        return ProcessingResult(
            success=True,
            output_path=output_path,
            original_size=original_size,
            new_size=new_size,
            category=category,
            elapsed_seconds=elapsed,
            extra=extra,
        )

    @staticmethod
    def _bitrate_extra(video_meta: Optional[VideoMetadata], new_size: int) -> dict:
        """Estimate the new bitrate from size/duration (compression doesn't
        change duration), avoiding a second ffprobe call just for metrics."""
        if video_meta is None or not video_meta.duration_s:
            return {}
        new_bitrate_mbps = (new_size * 8) / video_meta.duration_s / 1_000_000
        return {
            "original_bitrate_mbps": video_meta.bitrate_mbps,
            "new_bitrate_mbps": new_bitrate_mbps,
        }

    def describe_metadata(self, metadata: Any) -> list[str]:
        video_meta: VideoMetadata = metadata
        return [
            f"Codec: {reporting.format_codec(video_meta.video_codec)}",
            f"Resolution: {video_meta.width}x{video_meta.height}",
            f"FPS: {video_meta.fps:.0f}",
            f"Duration: {reporting.format_duration(video_meta.duration_s)}",
            f"Bitrate: {reporting.format_bitrate(video_meta.bitrate_mbps)}",
        ]

    def generate_thumbnail(self, file_path: Path) -> Optional[Path]:
        if not config.THUMBNAIL_ENABLED:
            return None
        return thumbnails.generate_thumbnail(file_path)

    def _categorize(self, video_meta: Optional[VideoMetadata]) -> str:
        """Duration first (Shorts), else output codec, else Long Videos."""
        if video_meta is not None and video_meta.duration_s <= config.SHORTS_MAX_DURATION_SECONDS:
            return "Videos/Shorts"

        profile_codec = compression_profiles.get_active_profile().codec
        if profile_codec in _HEVC_PROFILE_CODECS:
            return "Videos/HEVC"
        if profile_codec in _H264_PROFILE_CODECS:
            return "Videos/H264"
        return "Videos/Long Videos"
