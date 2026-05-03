"""Обёртки над ffmpeg/ffprobe + утилиты экранирования для filtergraph.

ВАЖНО: drawtext-фильтр чувствителен к экранированию. Безопасно подавать
пользовательский текст можно только через `textfile=` или после полного
экранирования всех специальных символов. См. write_overlay_text_file().
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile

from . import config
from .logging_setup import log


# ── Запуск ffmpeg ─────────────────────────────────────────────────────────────
async def run_ffmpeg(cmd: list[str], timeout: float = 180.0) -> bool:
    """Запускает ffmpeg и ждёт завершения. True — exit code 0."""
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
        log.warning("FFmpeg таймаут")
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
    """Проверяет наличие h264_nvenc.

    NB: NVENC сейчас детектится «на будущее» — текущий рендер использует libwebp.
    Если будет нужно — переключи рендер на nvenc через подмену кодека в render.py.
    """
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


# ── Экранирование для drawtext ────────────────────────────────────────────────
_VALID_COLOR_NAME_RE = re.compile(r"^[a-zA-Z]+$")
# 3, 4, 6 или 8 hex-цифр (#RGB, #RGBA, #RRGGBB, #RRGGBBAA), опциональный @<alpha>
_VALID_COLOR_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3,8}(?:@[0-9.]+)?$")

_ALLOWED_COLOR_NAMES: set[str] = {
    "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta",
    "orange", "purple", "pink", "brown", "gray", "grey", "lime", "navy",
    "teal", "silver", "gold", "violet", "indigo",
}


def sanitize_color(raw: str | None, default: str = "white") -> str:
    """Возвращает безопасную строку цвета для `fontcolor=`.

    Любой подозрительный ввод заменяется на `default`. Это защита от инъекций
    типа `red:fontfile=/etc/passwd`, `red,drawbox=...` и т.п.
    """
    if not raw:
        return default
    raw = raw.strip().lower()
    if raw in _ALLOWED_COLOR_NAMES:
        return raw
    if _VALID_COLOR_HEX_RE.match(raw):
        return raw if raw.startswith("#") else f"#{raw}"
    return default


def write_overlay_text_file(text: str, message_id: int, idx: int) -> str:
    """Сохраняет текст оверлея в файл и возвращает абсолютный путь.

    Используется с `drawtext=textfile=...` — это ИСКЛЮЧАЕТ filter-injection,
    т.к. ffmpeg читает текст как байты, а не парсит как часть filtergraph.
    """
    safe_name = f"ov_{message_id}_{idx}.txt"
    path = os.path.join(config.OVERLAY_TEXT_DIR, safe_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def make_temp_overlay_text_file(text: str) -> str:
    """Альтернатива write_overlay_text_file для одноразовых файлов с авто-именем.

    Чітко розрізняємо два моменти володіння fd:
      • до `os.fdopen` — fd ще «голий», на помилку треба `os.close(fd)`.
      • після `os.fdopen` — file-object бере fd у власність і закриє його сам
        у блоці `with`; повторний `os.close(fd)` дав би EBADF.
    """
    fd, path = tempfile.mkstemp(prefix="ov_", suffix=".txt", dir=config.OVERLAY_TEXT_DIR)
    try:
        fobj = os.fdopen(fd, "w", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise
    with fobj:
        fobj.write(text)
    return path


def escape_textfile_path(path: str) -> str:
    """Экранирует путь для подстановки в `drawtext=textfile=<path>`.

    В filtergraph надо экранировать `\\`, `:`, `'` (см. документацию ffmpeg).
    Файлы под TEMP_DIR содержат только безопасные ASCII-имена, но честнее
    отработать общий случай.
    """
    return path.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
