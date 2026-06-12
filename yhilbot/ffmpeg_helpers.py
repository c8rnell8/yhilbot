import asyncio
import os
import re
import tempfile

from . import config
from .logging_setup import log


async def run_ffmpeg(cmd: list[str], timeout: float = 180.0) -> bool:
    """Run ffmpeg and wait for it. Returns True on exit code 0."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            log.warning(f"FFmpeg {proc.returncode}: {err.decode(errors='replace')[-400:]}")
        return proc.returncode == 0
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        await proc.wait()
        log.warning("FFmpeg timed out")
        return False


async def get_video_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        out, _ = await proc.communicate()
        return float(out.decode().strip())
    except Exception:
        return 0.0


async def detect_gpu(timeout: float = 5.0) -> bool:
    # NVENC is probed but not used yet - rendering goes through libwebp.
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-encoders",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            await proc.wait()
            return False
        return b"h264_nvenc" in out
    except Exception:
        return False


_VALID_COLOR_NAME_RE = re.compile(r"^[a-zA-Z]+$")
# 3, 4, 6 or 8 hex digits (#RGB, #RGBA, #RRGGBB, #RRGGBBAA) with optional @<alpha>
_VALID_COLOR_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3,8}(?:@[0-9.]+)?$")

_ALLOWED_COLOR_NAMES: set[str] = {
    "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta",
    "orange", "purple", "pink", "brown", "gray", "grey", "lime", "navy",
    "teal", "silver", "gold", "violet", "indigo",
}


def sanitize_color(raw: str | None, default: str = "white") -> str:
    # Anything suspicious falls back to default - blocks injection like
    # `red:fontfile=/etc/passwd` or `red,drawbox=...`.
    if not raw:
        return default
    raw = raw.strip().lower()
    if raw in _ALLOWED_COLOR_NAMES:
        return raw
    if _VALID_COLOR_HEX_RE.match(raw):
        return raw if raw.startswith("#") else f"#{raw}"
    return default


def write_overlay_text_file(text: str, message_id: int, idx: int) -> str:
    # Used with drawtext=textfile=... so ffmpeg reads the text as bytes instead
    # of parsing it as part of the filtergraph - rules out filter injection.
    safe_name = f"ov_{message_id}_{idx}.txt"
    path = os.path.join(config.OVERLAY_TEXT_DIR, safe_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def make_temp_overlay_text_file(text: str) -> str:
    fd, path = tempfile.mkstemp(prefix="ov_", suffix=".txt", dir=config.OVERLAY_TEXT_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        os.close(fd)
        raise
    return path


def escape_textfile_path(path: str) -> str:
    # In a filtergraph, `\`, `:` and `'` have to be escaped.
    return path.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
