"""Configuration for Media Guardian.

Every tunable value lives here. No thresholds are hardcoded in the
logic modules (decision.py, video_optimizer.py, media_watcher.py, etc.).
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

WATCH_FOLDER = BASE_DIR / "incoming_media"
OUTPUT_FOLDER = BASE_DIR / "optimized_media"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv"}

# A file must report the same size across this many consecutive polls before
# it's treated as fully copied (protects against processing a partial upload/copy).
STABLE_POLL_SECONDS = 2.0
STABLE_REQUIRED_CYCLES = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Console + rotating file handler, so a long-running daily process keeps a
# durable history on disk instead of only ever-scrolling console output.
LOG_FILE = BASE_DIR / "media_guardian.log"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 5 * 1024 * 1024  # rotate after 5 MB
LOG_BACKUP_COUNT = 3  # keep this many rotated log files around

# ---------------------------------------------------------------------------
# Ignore rules (temp files / partial downloads / editor swap files)
# ---------------------------------------------------------------------------
# Any filename starting with one of these prefixes is ignored outright.
IGNORED_NAME_PREFIXES = {".", "~", "$"}
# Any filename ending with one of these suffixes is ignored outright
# (common temp/partial-download/editor-swap markers).
IGNORED_SUFFIXES = {".tmp", ".part", ".partial", ".crdownload", ".download"}

# ---------------------------------------------------------------------------
# Processed-file ledger (never process the same file twice, even across restarts)
# ---------------------------------------------------------------------------
STATE_DIR = BASE_DIR / "state"
PROCESSED_LEDGER_FILE = STATE_DIR / "processed_files.json"

# ---------------------------------------------------------------------------
# ffmpeg robustness
# ---------------------------------------------------------------------------
# Kill ffmpeg (and clean up) if a single encode runs longer than this instead
# of letting a hung/crashed process block a worker thread forever.
FFMPEG_TIMEOUT_SECONDS = 3600

# ---------------------------------------------------------------------------
# Smart compression decision thresholds (see decision.py for the rule engine)
# ---------------------------------------------------------------------------
MAX_SIZE_MB = 250  # files at/under this size are considered "reasonable"

HEVC_CODEC_NAMES = {"hevc", "h265"}
H264_CODEC_NAMES = {"h264", "avc1"}

# Bitrate at/above this triggers compression regardless of codec or size.
MAX_VIDEO_BITRATE_MBPS = 40.0

# Resolution above these dimensions triggers compression, downscaled to
# MAX_RESOLUTION_HEIGHT (width is derived to preserve aspect ratio).
MAX_RESOLUTION_WIDTH = 1920
MAX_RESOLUTION_HEIGHT = 1080

# Bitrate at/below this is treated as an "already efficient" signal.
TARGET_BITRATE_MBPS = 8.0

# ---------------------------------------------------------------------------
# Active encode profile (see compression_profiles.py for the full definitions)
# ---------------------------------------------------------------------------
ACTIVE_PROFILE = "SHARE"

# ---------------------------------------------------------------------------
# Plugin system (see plugins.py) -- every MediaProcessor subclass found in
# this package is auto-discovered at startup. Add new processors (images,
# audio, gifs, PDFs, ...) by dropping a new module in that package.
# ---------------------------------------------------------------------------
PROCESSORS_PACKAGE = "processors"

# ---------------------------------------------------------------------------
# Job queue / worker pool (see job_queue.py)
# ---------------------------------------------------------------------------
# How many compression jobs (ffmpeg processes) may run at once.
WORKER_COUNT = 2
# How many jobs may wait in the queue before submit() starts blocking (and
# logging) the caller -- this is the "don't launch unlimited ffmpeg
# processes" backpressure valve.
JOB_QUEUE_MAX_SIZE = 10

# ---------------------------------------------------------------------------
# Thumbnail generation (see thumbnails.py)
# ---------------------------------------------------------------------------
THUMBNAIL_ENABLED = True
THUMBNAIL_OUTPUT_FOLDER = BASE_DIR / "thumbnails"
# Where in the video to grab the thumbnail frame from.
THUMBNAIL_TIMESTAMP_SECONDS = 5.0
# Thumbnail width in pixels; height is derived to preserve aspect ratio.
THUMBNAIL_WIDTH = 320
THUMBNAIL_FORMAT = "jpg"  # "jpg" or "webp"

# ---------------------------------------------------------------------------
# Automatic folder organization (see organizer.py)
# ---------------------------------------------------------------------------
ORGANIZE_ENABLED = True
# "move" relocates the compressed file into the organized structure; "copy"
# leaves a copy in OUTPUT_FOLDER as well.
ORGANIZE_MODE = "move"
ORGANIZE_BASE_FOLDER = OUTPUT_FOLDER
# Videos at/under this duration are categorized as "Shorts" regardless of
# codec; longer videos are categorized by codec (HEVC/H264) or, failing
# that, "Long Videos".
SHORTS_MAX_DURATION_SECONDS = 60

# ---------------------------------------------------------------------------
# Performance metrics (see metrics.py)
# ---------------------------------------------------------------------------
METRICS_FILE = STATE_DIR / "metrics.json"
# Window used to compute the "files/hour" processing rate.
METRICS_RATE_WINDOW_SECONDS = 3600
