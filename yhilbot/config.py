import os
import shutil
import sys

from dotenv import load_dotenv

load_dotenv(dotenv_path="yhil.env")

TOKEN: str | None = os.getenv("DISCORD_TOKEN")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

MAX_INPUT_MB: int = int(os.getenv("MAX_INPUT_MB", "100"))
OUTPUT_LIMIT_MB: float = float(os.getenv("OUTPUT_LIMIT_MB", "24.5"))
MAX_VIDEO_SEC: int = int(os.getenv("MAX_VIDEO_SEC", "300"))

CONCURRENT_CONVERTS: int = int(os.getenv("CONCURRENT_CONVERTS", "2"))
CONCURRENT_RENDERS: int = int(os.getenv("CONCURRENT_RENDERS", "1"))
CAPTION_PARALLEL: int = int(os.getenv("CAPTION_PARALLEL", "4"))

TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/yhil_work")
CACHE_DIR: str = os.path.join(TEMP_DIR, "render_cache")
GIF_CACHE_DIR: str = os.path.join(TEMP_DIR, "gif_cache")
OVERLAY_TEXT_DIR: str = os.path.join(TEMP_DIR, "overlay_text")
LOG_PATH: str = os.getenv("LOG_PATH", "bot.log")
DB_PATH: str = os.path.join(TEMP_DIR, "editor.db")

EDITOR_TIMEOUT_SEC: int = int(os.getenv("EDITOR_TIMEOUT_SEC", "900"))
CLEANUP_INTERVAL_SEC: int = int(os.getenv("CLEANUP_INTERVAL_SEC", "120"))
CACHE_TTL_SEC: int = int(os.getenv("CACHE_TTL_SEC", "7200"))

# Gemini for /ai - free key from https://aistudio.google.com/apikey
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# Set once in on_ready after probing `ffmpeg -encoders`.
GPU_AVAILABLE: bool = False


def _parse_guild_ids() -> list[int]:
    raw = os.getenv("GUILD_IDS", os.getenv("GUILD_ID", ""))
    out: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            out.append(int(chunk))
    return out


GUILD_IDS: list[int] = _parse_guild_ids()


def validate_and_init_paths() -> None:
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set in yhil.env")
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found in PATH.")
    if not OWNER_ID:
        print("OWNER_ID is not set - /stats will be unavailable.", flush=True, file=sys.stderr)

    for d in (TEMP_DIR, CACHE_DIR, GIF_CACHE_DIR, OVERLAY_TEXT_DIR):
        os.makedirs(d, exist_ok=True)
    log_dir = os.path.dirname(os.path.abspath(LOG_PATH))
    os.makedirs(log_dir, exist_ok=True)


def set_gpu_available(value: bool) -> None:
    global GPU_AVAILABLE
    GPU_AVAILABLE = value
