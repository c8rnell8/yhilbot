"""Превью-кадр и доминирующий цвет (для embed)."""
from __future__ import annotations

import asyncio
import hashlib
import io
import os

import discord
from PIL import Image

from .. import config
from ..ffmpeg_helpers import run_ffmpeg
from .models import EditorSession


async def gen_preview_frame(sess: EditorSession) -> bytes | None:
    """Один JPEG-кадр в позиции курсора.

    Кэшируется по (source, round(cursor, 1)) — иначе каждый клик гонял ffmpeg.
    """
    if not sess.timeline.clips:
        return None
    clip = sess.timeline.clips[0]
    t = min(max(clip.start, sess.timeline.cursor), max(clip.start, clip.end - 0.05))
    width = min(sess.timeline.width, 480)

    cache_key = hashlib.md5(
        f"{clip.source}|{round(t, 1)}|{width}".encode()
    ).hexdigest()
    cache_path = os.path.join(config.GIF_CACHE_DIR, f"prev_{cache_key}.jpg")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except Exception:
            pass

    cmd = [
        "ffmpeg", "-y", "-ss", str(t), "-i", clip.source,
        "-vframes", "1", "-q:v", "4",
        "-vf", f"scale={width}:-1", cache_path,
    ]
    ok = await run_ffmpeg(cmd, timeout=10.0)
    if not ok or not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "rb") as f:
            return f.read()
    except Exception:
        return None


async def extract_dominant_color(frame: bytes) -> discord.Color:
    """Усреднённый цвет картинки → discord.Color (для рамки embed)."""
    try:
        def _do() -> discord.Color:
            img = Image.open(io.BytesIO(frame)).convert("RGB").resize((50, 50))
            pix = list(img.getdata())
            n = len(pix)
            return discord.Color.from_rgb(
                sum(p[0] for p in pix) // n,
                sum(p[1] for p in pix) // n,
                sum(p[2] for p in pix) // n,
            )

        return await asyncio.get_running_loop().run_in_executor(None, _do)
    except Exception:
        return discord.Color.blurple()
