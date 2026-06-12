import asyncio
import logging
import os

import aiohttp
import discord

from .. import config
from ..client import tree

log = logging.getLogger("yhilbot.webedit")

_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".gif", ".m4v"}
_POLL_SEC = 5


def _site() -> str:
    return (config.WEB_EDITOR_URL or "").rstrip("/")


@tree.command(
    name="webedit",
    description="Відкрити відео в браузерному редакторі (обрізка, текст, блюр, звук)",
)
@discord.app_commands.describe(video="Відеофайл для редагування")
async def webedit_cmd(interaction: discord.Interaction, video: discord.Attachment) -> None:
    if not _site() or not config.WEB_EDITOR_TOKEN:
        await interaction.response.send_message(
            "Веб-редактор не налаштований (WEB_EDITOR_URL / WEB_EDITOR_TOKEN).",
            ephemeral=True,
        )
        return

    ext = os.path.splitext(video.filename or "")[1].lower()
    if ext not in _VIDEO_EXTS:
        await interaction.response.send_message(
            f"Це не відео. Підтримуються: {', '.join(sorted(_VIDEO_EXTS))}",
            ephemeral=True,
        )
        return
    if video.size > config.MAX_INPUT_MB * 1024 * 1024:
        await interaction.response.send_message(
            f"Файл завеликий ({video.size / 1024 / 1024:.0f} МБ). Ліміт {config.MAX_INPUT_MB} МБ.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        data = await video.read()
    except Exception as e:  # noqa: BLE001
        await interaction.followup.send(f"Не зміг скачати файл з Discord: {e}")
        return

    form = aiohttp.FormData()
    form.add_field("file", data, filename=video.filename, content_type=video.content_type or "video/mp4")
    form.add_field("discordUserId", str(interaction.user.id))
    form.add_field("discordUsername", interaction.user.name)
    form.add_field("discordChannelId", str(interaction.channel_id or ""))
    form.add_field("discordGuildId", str(interaction.guild_id or ""))

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"{_site()}/api/editor/sessions",
                data=form,
                headers={"X-Yhilbot-Token": config.WEB_EDITOR_TOKEN},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as res:
                j = await res.json(content_type=None)
                if res.status != 201 and res.status != 200:
                    await interaction.followup.send(
                        f"Сайт відхилив завантаження ({res.status}): {j.get('error', '')}"
                    )
                    return
    except Exception as e:  # noqa: BLE001
        await interaction.followup.send(f"Не достукався до сайту: {e}")
        return

    session_id = j.get("id")
    url = f"{_site()}/ua/editor/{session_id}"
    await interaction.followup.send(
        f"🎬 Редактор готовий: {url}\n"
        f"Зроби монтаж і натисни «Рендер» — я принесу результат сюди сам "
        f"(стежу {config.EDITOR_TIMEOUT_SEC // 60} хв)."
    )

    asyncio.create_task(_watch_and_deliver(interaction, session_id))


async def _watch_and_deliver(interaction: discord.Interaction, session_id: str) -> None:
    """Poll the site until the render lands, then post the file back."""
    deadline = asyncio.get_event_loop().time() + config.EDITOR_TIMEOUT_SEC
    delivered_marker = None

    async with aiohttp.ClientSession() as http:
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(_POLL_SEC)
            try:
                async with http.get(
                    f"{_site()}/api/editor/sessions/{session_id}",
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as res:
                    if res.status != 200:
                        continue
                    s = await res.json(content_type=None)
            except Exception:  # noqa: BLE001 - transient network errors are fine
                continue

            output = s.get("output")
            if s.get("status") != "rendered" or not output:
                continue
            # Re-renders update the timestamp; deliver each new result once.
            marker = (output.get("bytes"), s.get("updatedAt"))
            if marker == delivered_marker:
                continue

            size_mb = (output.get("bytes") or 0) / 1024 / 1024
            if size_mb > config.OUTPUT_LIMIT_MB:
                await _say(
                    interaction,
                    f"Готово, але файл {size_mb:.1f} МБ — більший за мій ліміт "
                    f"{config.OUTPUT_LIMIT_MB:.0f} МБ. Завантаж напряму: "
                    f"{_site()}/api/editor/sessions/{session_id}/output "
                    f"(або в редакторі постав ліміт розміру і відрендери ще раз).",
                )
                delivered_marker = marker
                continue

            try:
                async with http.get(
                    f"{_site()}/api/editor/sessions/{session_id}/output",
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as res:
                    if res.status != 200:
                        continue
                    blob = await res.read()
            except Exception as e:  # noqa: BLE001
                log.warning("webedit: failed to pull output %s: %s", session_id, e)
                continue

            ext = output.get("ext") or ".mp4"
            file = discord.File(
                fp=__import__("io").BytesIO(blob), filename=f"yhil_edit{ext}"
            )
            await _say(interaction, "✅ Монтаж готовий:", file=file)
            delivered_marker = marker

        if delivered_marker is None:
            await _say(
                interaction,
                f"Час вийшов — рендер так і не з'явився. Сесія: {_site()}/ua/editor/{session_id}",
            )


async def _say(interaction: discord.Interaction, text: str, file: discord.File | None = None) -> None:
    try:
        if file:
            await interaction.followup.send(text, file=file)
        else:
            await interaction.followup.send(text)
    except Exception:  # noqa: BLE001 - webhook may expire after 15 min
        channel = interaction.channel
        if channel and hasattr(channel, "send"):
            try:
                if file:
                    await channel.send(text, file=file)
                else:
                    await channel.send(text)
            except Exception:
                log.warning("webedit: could not deliver result to channel")
