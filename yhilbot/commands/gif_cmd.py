"""/gif — конвертация видео/изображения в анимацию."""
from __future__ import annotations

import asyncio
import os

import discord
from discord import app_commands

from .. import config
from ..client import tree
from ..ffmpeg_helpers import get_video_duration, run_ffmpeg
from ..logging_setup import log
from ..media_utils import get_media_from_context, safe_save
from ..queue_mgr import queue_remove, queue_wait
from ..stats import stats

CONVERT_LIMIT: asyncio.Semaphore | None = None


def _convert_limit() -> asyncio.Semaphore:
    global CONVERT_LIMIT
    if CONVERT_LIMIT is None:
        CONVERT_LIMIT = asyncio.Semaphore(config.CONCURRENT_CONVERTS)
    return CONVERT_LIMIT


@tree.command(name="gif", description="Конвертирует медиа в анимацию (GIF/WebP)")
@app_commands.describe(media="Видео или изображение (можно не указывать — возьмёт из чата)")
async def gif_cmd(interaction: discord.Interaction, media: discord.Attachment | None = None) -> None:
    await interaction.response.defer(thinking=True)
    if not media:
        media = await get_media_from_context(interaction)
    if not media:
        await interaction.followup.send("❌ Медиа не найдено.")
        return
    if not media.content_type or not (
        media.content_type.startswith("video/") or media.content_type.startswith("image/")
    ):
        await interaction.followup.send("❌ Поддерживаются только видео и изображения.")
        return
    if media.size > config.MAX_INPUT_MB * 1024 * 1024:
        await interaction.followup.send(f"❌ Файл > {config.MAX_INPUT_MB} МБ.")
        return
    if not await queue_wait(interaction):
        return

    ext = media.filename.rsplit(".", 1)[-1].lower() if "." in media.filename else "bin"
    inp = os.path.join(config.TEMP_DIR, f"gif_i_{interaction.id}.{ext}")
    is_video = media.content_type.startswith("video/")
    out_ext = "webp" if is_video else "gif"
    out = os.path.join(config.TEMP_DIR, f"gif_o_{interaction.id}.{out_ext}")

    try:
        if not await safe_save(media, inp):
            await interaction.followup.send("❌ Не удалось скачать файл.")
            return

        duration = min(await get_video_duration(inp), 20.0) if is_video else 0.0

        async with _convert_limit():
            target = int(config.OUTPUT_LIMIT_MB * 1024 * 1024)
            scale = 1920 if is_video else 3840
            fps, quality = (24, 95) if is_video else (0, 0)
            attempts, success = 0, False

            while attempts <= 4:
                if is_video:
                    vf = f"fps={fps},scale={scale}:-1:flags=lanczos,format=rgba"
                    cmd = [
                        "ffmpeg", "-y", "-threads", "2", "-i", inp, "-vf", vf,
                        "-t", str(duration), "-c:v", "libwebp", "-lossless", "0",
                        "-quality", str(quality), "-compression_level", "6",
                        "-loop", "0", "-preset", "default", "-an", out,
                    ]
                else:
                    fc = (
                        f"scale={scale}:-1:flags=lanczos,split[s0][s1];"
                        f"[s0]palettegen=max_colors=256:stats_mode=single[p];"
                        f"[s1][p]paletteuse=dither=bayer:bayer_scale=1[out]"
                    )
                    cmd = [
                        "ffmpeg", "-y", "-threads", "2", "-i", inp,
                        "-filter_complex", fc, "-map", "[out]", "-loop", "0", out,
                    ]

                ok = await run_ffmpeg(cmd)
                if ok and os.path.exists(out) and os.path.getsize(out) <= target:
                    success = True
                    break

                attempts += 1
                if not os.path.exists(out):
                    break
                ratio = (target / max(1, os.path.getsize(out))) ** 0.6
                if is_video:
                    scale = max(640, int(scale * ratio))
                    fps = max(12, int(fps * ratio))
                    quality = max(50, quality - 15)
                else:
                    scale = max(1080, int(scale * ratio))

            if not success or not os.path.exists(out) or os.path.getsize(out) > target:
                stats.inc("gif_fail")
                await interaction.followup.send("⚠️ Не удалось уложить файл в лимит Discord.")
                return

            sz = os.path.getsize(out) / 1024
            try:
                await interaction.followup.send(file=discord.File(out, filename=f"result.{out_ext}"))
                stats.inc("gif_ok")
                log.info(f"✅ GIF: {interaction.user} | {out_ext.upper()} | {sz:.0f} КБ")
            except discord.HTTPException as e:
                stats.inc("gif_fail")
                msg = (
                    "⚠️ Discord отклонил файл (превышен лимит)."
                    if e.status == 413 else "❌ Ошибка отправки."
                )
                await interaction.followup.send(msg)

    except Exception as e:
        stats.inc("gif_fail")
        log.exception(f"GIF critical [{interaction.user}]: {e}")
        if not interaction.is_expired():
            try:
                await interaction.followup.send("❌ Внутренняя ошибка.")
            except Exception:
                pass
    finally:
        await queue_remove(interaction.id)
        for f in (inp, out):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
