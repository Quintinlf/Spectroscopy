"""Human-readable console report blocks.

These print the pretty, fixed-format report the tool is expected to show
before/after processing. Structured, greppable logging (for the rotating log
file) happens separately via `logging` calls elsewhere -- this module is
purely about the console presentation layer.

Deliberately processor-agnostic: print_detection_report() takes plain
description lines (supplied by MediaProcessor.describe_metadata()) rather
than a concrete metadata type, so it works the same for video, images,
audio, or any future processor without this module needing to know about
any of them.
"""

from __future__ import annotations

import sys

from processing import ProcessingDecision

SEPARATOR = "-" * 50

_CODEC_DISPLAY_OVERRIDES = {
    "h264": "H264",
    "hevc": "HEVC",
    "h265": "HEVC",
    "vp9": "VP9",
    "av1": "AV1",
}


def format_size(num_bytes: float) -> str:
    if num_bytes >= 1024 ** 3:
        return f"{num_bytes / 1024 ** 3:.2f} GB"
    return f"{num_bytes / 1024 ** 2:.0f} MB"


def format_bitrate(mbps: float) -> str:
    return f"{mbps:.0f} Mbps"


def format_duration(seconds: float) -> str:
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    return f"{minutes}m{secs:02d}s"


def format_codec(codec_name: str) -> str:
    return _CODEC_DISPLAY_OVERRIDES.get(codec_name.lower(), codec_name.upper())


def _safe_print(text: str) -> None:
    """Print text, falling back to ASCII-safe substitutes if the console
    codepage can't render ✓/✗ (common on default Windows consoles).

    Always flushes: stdout is block-buffered when piped/redirected (e.g. to
    a log file, or when this process is killed abruptly), and this report
    is meant to be visible immediately, not lost in a buffer.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        replaced = text.replace("\u2713", "[COMPRESS]").replace("\u2717", "[SKIP]")
        try:
            print(replaced)
        except UnicodeEncodeError:
            print(replaced.encode("ascii", errors="replace").decode("ascii"))
    finally:
        sys.stdout.flush()


def print_detection_report(
    name: str, description_lines: list[str], size_bytes: int, decision: ProcessingDecision,
) -> None:
    """Print the 'Detected: ... / Decision: ...' block for one file.

    `description_lines` comes from MediaProcessor.describe_metadata() -- this
    function only adds the file name, size, and decision around it, so the
    same block works for any processor type.
    """
    symbol = "\u2713" if decision.should_process else "\u2717"
    verb = "Compress" if decision.should_process else "Skip"
    lines = [
        SEPARATOR,
        f"Detected: {name}",
        "",
        *description_lines,
        f"Size: {format_size(size_bytes)}",
        "",
        "Decision:",
        f"{symbol} {verb}",
        "Reason:",
        decision.reason_text,
    ]
    _safe_print("\n".join(lines))


def print_compression_result(original_bytes: int, new_bytes: int) -> None:
    """Print the 'Compression complete. / Original / New / Saved' block."""
    saved_bytes = original_bytes - new_bytes
    saved_pct = (saved_bytes / original_bytes * 100) if original_bytes else 0.0
    lines = [
        "",
        "Compression complete.",
        "",
        "Original:",
        format_size(original_bytes),
        "",
        "New:",
        format_size(new_bytes),
        "",
        "Saved:",
        f"{format_size(saved_bytes)} ({saved_pct:.0f}%)",
        "",
        SEPARATOR,
    ]
    _safe_print("\n".join(lines))


def print_skip_footer() -> None:
    """Close out the report block for a file that was skipped (no compression)."""
    _safe_print("\n" + SEPARATOR)


def print_error_footer(message: str) -> None:
    """Close out the report block for a file that failed to process."""
    _safe_print(f"\nProcessing failed: {message}\n{SEPARATOR}")
