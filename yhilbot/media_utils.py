import asyncio
import os

import discord

from .logging_setup import log


async def safe_save(att: discord.Attachment, path: str, retries: int = 3) -> bool:
    """Download an attachment with retries, cleaning up partial files on failure."""
    for attempt in range(retries):
        try:
            await att.save(path)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True
        except Exception as e:
            log.warning(f"download attempt {attempt + 1}/{retries}: {e}")
            await asyncio.sleep(1.0)

    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    return False


async def get_media_from_context(
    interaction: discord.Interaction,
    content_filter: tuple = ("video/", "image/"),
) -> discord.Attachment | None:
    """First matching attachment from the last 15 messages in the channel.

    Slash commands have no `interaction.message`, so there's no reply branch here.
    """
    try:
        async for msg in interaction.channel.history(limit=15):
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith(content_filter):
                    return att
    except Exception as e:
        log.warning(f"get_media_from_context: history scan failed: {e}")
    return None
