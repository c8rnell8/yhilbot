"""/caption — мем-заголовок поверх изображения."""
from __future__ import annotations

import asyncio
import io

import discord
from discord import app_commands

from .. import config
from ..caption_render import draw_caption_sync
from ..client import tree
from ..logging_setup import log
from ..media_utils import get_media_from_context
from ..stats import stats

CAPTION_LIMIT: asyncio.Semaphore | None = None


def _caption_limit() -> asyncio.Semaphore:
    global CAPTION_LIMIT
    if CAPTION_LIMIT is None:
        CAPTION_LIMIT = asyncio.Semaphore(config.CAPTION_PARALLEL)
    return CAPTION_LIMIT


@tree.command(name="caption", description="Добавляет мем-заголовок на картинку")
@app_commands.describe(text="Текст заголовка", media="Изображение (опционально)")
async def caption_cmd(
    interaction: discord.Interaction,
    text: str,
    media: discord.Attachment | None = None,
) -> None:
    await interaction.response.defer(thinking=True)
    if not media:
        media = await get_media_from_context(interaction, content_filter=("image/",))
    if not media:
        await interaction.followup.send("❌ Изображение не найдено.")
        return
    if not media.content_type or not media.content_type.startswith("image/"):
        await interaction.followup.send("❌ Поддерживаются только изображения.")
        return
    if media.size > config.MAX_INPUT_MB * 1024 * 1024:
        await interaction.followup.send(f"❌ Файл > {config.MAX_INPUT_MB} МБ.")
        return

    async with _caption_limit():
        try:
            img_bytes = await media.read()
            if not img_bytes:
                await interaction.followup.send("❌ Не удалось скачать.")
                return
            ext = media.filename.rsplit(".", 1)[-1].lower() if "." in media.filename else "png"
            fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "gif": "PNG"}
            fmt = fmt_map.get(ext, "PNG")
            # Output extension must match the produced format, иначе клиент Discord
            # видит .gif с PNG-байтами и иногда не показывает превью.
            out_ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(fmt, "png")
            res = await asyncio.get_running_loop().run_in_executor(
                None, draw_caption_sync, img_bytes, text, fmt
            )
            try:
                await interaction.followup.send(
                    file=discord.File(io.BytesIO(res), filename=f"caption.{out_ext}")
                )
                stats.inc("caption_ok")
                log.info(f"✅ Caption: {interaction.user} | {text!r}")
            except discord.HTTPException as e:
                stats.inc("caption_fail")
                log.warning(f"caption_cmd: send failed: {e}")
        except Exception as e:
            stats.inc("caption_fail")
            log.exception(f"Caption [{interaction.user}]: {e}")
            if not interaction.is_expired():
                try:
                    await interaction.followup.send("❌ Ошибка обработки.")
                except Exception:
                    pass
