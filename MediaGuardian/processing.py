"""Core processor contract shared by every media type Media Guardian handles.

This module defines the abstraction only -- it must never import a concrete
processor (that would create a cycle with processors/*). Concrete processors
live in the processors/ package and are auto-discovered by plugins.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ProcessingDecision:
    """Generic outcome of MediaProcessor.analyze().

    Deliberately processor-agnostic: video-specific detail (e.g. a target
    downscale height) belongs in `extra`, not as a dedicated field here, so
    adding a new processor type never requires touching this dataclass.
    """

    should_process: bool
    reasons: list[str] = field(default_factory=list)
    estimated_savings: Optional[float] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def reason_text(self) -> str:
        return " + ".join(self.reasons) if self.reasons else "No rules triggered"


@dataclass
class ProcessingResult:
    """Generic outcome of MediaProcessor.process()."""

    success: bool
    output_path: Optional[Path] = None
    original_size: int = 0
    new_size: Optional[int] = None
    # Organizer hint, e.g. "Videos/HEVC". None means "don't organize this file".
    category: Optional[str] = None
    error: Optional[str] = None
    # Wall-clock seconds spent in process(); used by metrics.py.
    elapsed_seconds: float = 0.0
    # Processor-specific extras metrics.py may look at (e.g. bitrate before/
    # after, for the "average bitrate reduction" stat). Optional by design so
    # processors that don't have a bitrate concept (images, PDFs, ...) simply
    # leave this empty.
    extra: dict[str, Any] = field(default_factory=dict)


class MediaProcessor(ABC):
    """Base class for anything that can inspect and act on a media file.

    Implementations are auto-discovered from config.PROCESSORS_PACKAGE by
    plugins.py; nothing else in the codebase needs to know a processor
    exists for it to start being used.
    """

    name: str = "unnamed_processor"

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Return True if this processor knows how to handle file_path."""
        raise NotImplementedError

    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Optional[Any]:
        """Return processor-specific metadata for file_path, or None if the
        file can't be read/understood."""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, metadata: Any, file_path: Path, size_bytes: int) -> ProcessingDecision:
        """Decide whether file_path is worth processing, and why."""
        raise NotImplementedError

    @abstractmethod
    def process(self, file_path: Path, decision: ProcessingDecision) -> ProcessingResult:
        """Actually process file_path per the given decision."""
        raise NotImplementedError

    def describe_metadata(self, metadata: Any) -> list[str]:
        """Human-readable lines describing `metadata` for the console report.

        Override to control exactly what the detection report shows; the
        default is a reasonable fallback for a processor that hasn't bothered.
        """
        return [str(metadata)]

    def generate_thumbnail(self, file_path: Path) -> Optional[Path]:
        """Optional hook: generate a preview image for file_path.

        Default is a no-op (returns None). Processors that support previews
        (video, image, ...) should override this.
        """
        return None
