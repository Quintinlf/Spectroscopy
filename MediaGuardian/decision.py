"""Extensible rule-based engine for deciding whether a video is worth compressing.

Design goals:
    - No long if/elif chain. Each rule is a small, independent class that only
      looks at a RuleContext and returns a RuleResult (or None if it doesn't
      apply). Rules never call or know about each other.
    - Adding a new rule (battery-powered mode, CPU load, free disk space,
      cloud upload limits, archive mode, phone-vs-screen-recording presets,
      ...) means writing one new CompressionRule subclass and appending it to
      DEFAULT_RULES. Nothing else needs to change.
    - The engine's resolution policy lives in exactly one place
      (CompressionEngine.evaluate), so changing how conflicting votes are
      resolved never requires touching individual rules.

Current resolution policy: any rule that votes COMPRESS wins outright (a
genuine reason to compress -- oversized, high bitrate, wrong codec, too high
a resolution -- always outweighs a merely "this looks efficient" signal). If
no rule votes COMPRESS, the file is skipped and every SKIP vote is reported
as a reason.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import config
from metadata import VideoMetadata


class CompressionVote(Enum):
    """What a single rule thinks should happen to this file."""

    COMPRESS = "compress"
    SKIP = "skip"


@dataclass(frozen=True)
class RuleContext:
    """Everything a rule is allowed to look at when making its decision.

    Kept intentionally narrow today (metadata + size). Future rules that need
    system state (battery, CPU, disk, network) should extend this dataclass
    with new optional fields rather than reaching for globals, so every rule
    stays a pure function of its input and stays easy to unit test.
    """

    metadata: VideoMetadata
    size_bytes: int

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass(frozen=True)
class RuleResult:
    """The outcome of one rule firing."""

    reason: str
    vote: CompressionVote
    downscale_height: Optional[int] = None
    estimated_savings: Optional[float] = None


class CompressionRule(ABC):
    """Base class for a single, independent compression rule."""

    name: str = "unnamed_rule"

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        """Return a RuleResult if this rule applies, else None."""
        raise NotImplementedError


@dataclass
class CompressionDecision:
    """Final, aggregated output of the rule engine for one file."""

    compress: bool
    reasons: list[str] = field(default_factory=list)
    estimated_savings: Optional[float] = None
    downscale_height: Optional[int] = None

    @property
    def reason_text(self) -> str:
        return " + ".join(self.reasons) if self.reasons else "No rules triggered"


# ---------------------------------------------------------------------------
# Default rules -- one class per bullet point in the spec. Each is fully
# self-contained and reads its own thresholds from config.py.
# ---------------------------------------------------------------------------


class SizeExceedsLimitRule(CompressionRule):
    name = "size_exceeds_limit"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.size_mb > config.MAX_SIZE_MB:
            return RuleResult(
                reason=f"File exceeds size limit ({ctx.size_mb:.0f} MB > {config.MAX_SIZE_MB} MB)",
                vote=CompressionVote.COMPRESS,
            )
        return None


class H264CodecRule(CompressionRule):
    name = "h264_codec"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.metadata.video_codec in config.H264_CODEC_NAMES:
            return RuleResult(reason="Codec is H.264", vote=CompressionVote.COMPRESS)
        return None


class BitrateExceedsRule(CompressionRule):
    name = "bitrate_exceeds_maximum"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.metadata.bitrate_mbps >= config.MAX_VIDEO_BITRATE_MBPS:
            # Rough heuristic: encoding down to the target bitrate saves
            # roughly the proportional difference. Real savings depend on
            # content and codec, so treat this purely as an estimate.
            savings = max(0.0, 1 - (config.TARGET_BITRATE_MBPS / ctx.metadata.bitrate_mbps))
            return RuleResult(
                reason=f"Bitrate exceeds maximum ({ctx.metadata.bitrate_mbps:.1f} Mbps >= {config.MAX_VIDEO_BITRATE_MBPS} Mbps)",
                vote=CompressionVote.COMPRESS,
                estimated_savings=savings,
            )
        return None


class ResolutionExceedsRule(CompressionRule):
    name = "resolution_exceeds_maximum"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.metadata.width > config.MAX_RESOLUTION_WIDTH or ctx.metadata.height > config.MAX_RESOLUTION_HEIGHT:
            return RuleResult(
                reason=f"Resolution exceeds maximum ({ctx.metadata.width}x{ctx.metadata.height} > "
                       f"{config.MAX_RESOLUTION_WIDTH}x{config.MAX_RESOLUTION_HEIGHT})",
                vote=CompressionVote.COMPRESS,
                downscale_height=config.MAX_RESOLUTION_HEIGHT,
            )
        return None


class AlreadyHevcRule(CompressionRule):
    name = "already_hevc"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.metadata.video_codec in config.HEVC_CODEC_NAMES:
            return RuleResult(reason="Already HEVC", vote=CompressionVote.SKIP)
        return None


class BelowTargetBitrateRule(CompressionRule):
    name = "below_target_bitrate"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.metadata.bitrate_mbps <= config.TARGET_BITRATE_MBPS:
            return RuleResult(reason="Already below target bitrate", vote=CompressionVote.SKIP)
        return None


class BelowSizeThresholdRule(CompressionRule):
    name = "below_size_threshold"

    def evaluate(self, ctx: RuleContext) -> Optional[RuleResult]:
        if ctx.size_mb <= config.MAX_SIZE_MB:
            return RuleResult(reason="Already below size threshold", vote=CompressionVote.SKIP)
        return None


DEFAULT_RULES: list[CompressionRule] = [
    SizeExceedsLimitRule(),
    H264CodecRule(),
    BitrateExceedsRule(),
    ResolutionExceedsRule(),
    AlreadyHevcRule(),
    BelowTargetBitrateRule(),
    BelowSizeThresholdRule(),
]


class CompressionEngine:
    """Runs a set of independent rules and resolves them into one decision."""

    def __init__(self, rules: Optional[list[CompressionRule]] = None):
        self.rules = rules if rules is not None else list(DEFAULT_RULES)

    def evaluate(self, ctx: RuleContext) -> CompressionDecision:
        compress_results: list[RuleResult] = []
        skip_results: list[RuleResult] = []

        for rule in self.rules:
            result = rule.evaluate(ctx)
            if result is None:
                continue
            if result.vote is CompressionVote.COMPRESS:
                compress_results.append(result)
            else:
                skip_results.append(result)

        if compress_results:
            downscale_height = next(
                (r.downscale_height for r in compress_results if r.downscale_height is not None), None
            )
            estimated_savings = next(
                (r.estimated_savings for r in compress_results if r.estimated_savings is not None), None
            )
            return CompressionDecision(
                compress=True,
                reasons=[r.reason for r in compress_results],
                estimated_savings=estimated_savings,
                downscale_height=downscale_height,
            )

        return CompressionDecision(
            compress=False,
            reasons=[r.reason for r in skip_results],
        )


DEFAULT_ENGINE = CompressionEngine(DEFAULT_RULES)
