"""/webedit — загрузка видео в веб-редактор yhilyanty-site и доставка результата.

Поток:
  1. Пользователь вызывает `/webedit media:<file>`.
  2. Бот скачивает вложение и POST'ит его в `WEB_EDITOR_URL/api/editor/sessions`.
  3. Сайт возвращает `editorUrl` — ссылку на веб-редактор.
  4. Бот отвечает в чат сообщением с этой ссылкой.
  5. Бот в фоне поллит `GET /api/editor/sessions/{id}` каждые
     `WEB_EDITOR_POLL_SEC` секунд.
  6. Когда `status == "rendered"` — бот скачивает результат, постит в канал
     как вложение с пингом юзера.

Все обращения к сайту используют общий секрет `WEB_EDITOR_TOKEN`
в заголовке `X-Yhilbot-Token`.
"""
from __future__ import annotations

import asyncio
import io
import time
from typing import Any

import aiohttp
import discord
from discord import app_commands

from .. import config
from ..client import tree
from ..logging_setup import log


def _is_configured() -> bool:
    return bool(config.WEB_EDITOR_URL)


def _headers() -> dict[str, str]:
    h = {"User-Agent": "yhilbot/webedit"}
    if config.WEB_EDITOR_TOKEN:
        h["X-Yhilbot-Token"] = config.WEB_EDITOR_TOKEN
    return h


async def _upload_to_editor(
    session: aiohttp.ClientSession,
    *,
    filename: str,
    payload: bytes,
    content_type: str,
    interaction: discord.Interaction,
) -> dict[str, Any]:
    form = aiohttp.FormData()
    form.add_field("file", payload, filename=filename, content_type=content_type)
    form.add_field("locale", config.WEB_EDITOR_LOCALE)
    form.add_field("discord_user_id", str(interaction.user.id))
    form.add_field("discord_username", interaction.user.display_name or interaction.user.name)
    if interaction.channel_id:
        form.add_field("discord_channel_id", str(interaction.channel_id))
    if interaction.guild_id:
        form.add_field("discord_guild_id", str(interaction.guild_id))

    url = f"{config.WEB_EDITOR_URL}/api/editor/sessions"
    async with session.post(url, headers=_headers(), data=form) as resp:
        text = await resp.text()
        if resp.status >= 400:
            raise RuntimeError(f"upload failed: HTTP {resp.status}: {text[:300]}")
        try:
            return await _safe_json(text)
        except Exception as e:
            raise RuntimeError(f"upload returned non-json: {text[:300]}") from e


async def _safe_json(text: str) -> dict[str, Any]:
    import json

    return json.loads(text)


async def _poll_status(
    session: aiohttp.ClientSession, session_id: str
) -> dict[str, Any]:
    url = f"{config.WEB_EDITOR_URL}/api/editor/sessions/{session_id}"
    async with session.get(url, headers=_headers()) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"status failed: HTTP {resp.status}")
        return await resp.json()


async def _download_output(
    session: aiohttp.ClientSession, session_id: str
) -> bytes:
    url = f"{config.WEB_EDITOR_URL}/api/editor/sessions/{session_id}/output?dl=1"
    async with session.get(url, headers=_headers()) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"download failed: HTTP {resp.status}")
        return await resp.read()


async def _wait_and_deliver(
    interaction: discord.Interaction, session_id: str, editor_url: str
) -> None:
    """Поллим сайт, при готовности постим результат в канал."""
    timeout = aiohttp.ClientTimeout(total=config.WEB_EDITOR_TIMEOUT_SEC + 60)
    started = time.time()
    deadline = started + config.WEB_EDITOR_TIMEOUT_SEC
    last_status: str | None = None

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while time.time() < deadline:
            try:
                data = await _poll_status(session, session_id)
            except Exception as e:
                log.warning("webedit:poll_error session=%s err=%s", session_id, e)
                await asyncio.sleep(config.WEB_EDITOR_POLL_SEC)
                continue

            status = str(data.get("status") or "")
            if status != last_status:
                log.info("webedit:status session=%s status=%s", session_id, status)
                last_status = status

            if status == "rendered":
                output = data.get("output") or {}
                ext = output.get("ext") or ".mp4"
                try:
                    payload = await _download_output(session, session_id)
                except Exception as e:
                    log.error("webedit:download_failed session=%s err=%s", session_id, e)
                    await interaction.followup.send(
                        f"❌ Готовий рендер не вдалося завантажити з сайту: {e}",
                        ephemeral=True,
                    )
                    return
                file = discord.File(io.BytesIO(payload), filename=f"yhilbot-{session_id}{ext}")
                channel = interaction.channel
                content = (
                    f"<@{interaction.user.id}> ✓ Готово — рендер з [веб-редактора]({editor_url})."
                )
                try:
                    if channel is not None and hasattr(channel, "send"):
                        await channel.send(content=content, file=file)
                    else:
                        await interaction.followup.send(content=content, file=file)
                except discord.HTTPException as e:
                    # Файл, ймовірно, занадто великий для каналу — даємо лінк
                    log.warning("webedit:send_failed_falling_back session=%s err=%s", session_id, e)
                    download_url = (
                        f"{config.WEB_EDITOR_URL}/api/editor/sessions/{session_id}/output?dl=1"
                    )
                    await interaction.followup.send(
                        content=(
                            f"<@{interaction.user.id}> ✓ Готово, але файл занадто великий "
                            f"для Discord-каналу. Завантаж напряму: {download_url}"
                        ),
                    )
                return

            if status == "failed":
                err = data.get("error") or "unknown"
                await interaction.followup.send(
                    content=f"❌ Рендер з [веб-редактора]({editor_url}) впав: `{err[:300]}`",
                    ephemeral=True,
                )
                return

            await asyncio.sleep(config.WEB_EDITOR_POLL_SEC)

        await interaction.followup.send(
            content=(
                f"⏱ Час очікування рендера вийшов ({config.WEB_EDITOR_TIMEOUT_SEC}s). "
                f"Якщо ще не натиснув «Готово» — натисни тут: {editor_url}"
            ),
            ephemeral=True,
        )


@tree.command(
    name="webedit",
    description="Відкрити відео у веб-редакторі — отримаєш гіфку/відео назад у канал",
)
@app_commands.describe(media="Відео-файл (MP4, MOV, WebM, GIF — до 100 МБ)")
async def webedit_cmd(
    interaction: discord.Interaction,
    media: discord.Attachment,
) -> None:
    if not _is_configured():
        await interaction.response.send_message(
            "❌ Веб-редактор не налаштований: WEB_EDITOR_URL пустий у `yhil.env`.",
            ephemeral=True,
        )
        return

    # Базова перевірка розміру
    max_bytes = config.MAX_INPUT_MB * 1024 * 1024
    if media.size and media.size > max_bytes:
        await interaction.response.send_message(
            f"❌ Файл задурий: {media.size // (1024 * 1024)}MB > MAX_INPUT_MB={config.MAX_INPUT_MB}.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    # Завантажуємо файл з Discord CDN, потім аплоадимо на сайт.
    timeout = aiohttp.ClientTimeout(total=120)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = await media.read()
            data = await _upload_to_editor(
                session,
                filename=media.filename or "input.mp4",
                payload=payload,
                content_type=media.content_type or "application/octet-stream",
                interaction=interaction,
            )
    except Exception as e:
        log.exception("webedit:upload_failed user=%s err=%s", interaction.user.id, e)
        await interaction.followup.send(
            f"❌ Не вдалося завантажити на сайт: `{e}`", ephemeral=True
        )
        return

    session_id = str(data.get("id") or "")
    editor_url = str(data.get("editorUrl") or "")
    if not session_id or not editor_url:
        await interaction.followup.send(
            "❌ Сайт повернув відповідь без `id`/`editorUrl`.", ephemeral=True
        )
        return

    src = data.get("source") or {}
    duration = src.get("duration") or 0
    width = src.get("width") or 0
    height = src.get("height") or 0
    embed = discord.Embed(
        title="Веб-редактор готовий",
        description=(
            f"**Відкрий**: {editor_url}\n\n"
            f"Зроби обрізку, додай текст/блюр/кроп, обери формат і натисни **Готово**.\n"
            f"Бот сам пришле готовий файл сюди, як тільки рендер завершиться."
        ),
        color=0xFBBF24,
    )
    embed.add_field(name="Сесія", value=f"`{session_id}`", inline=True)
    embed.add_field(
        name="Джерело",
        value=f"{int(duration)}s · {width}×{height}",
        inline=True,
    )
    embed.set_footer(text="Лінк індивідуальна — не передавай посторонім.")
    await interaction.followup.send(embed=embed)

    # Запускаємо фонове очікування — не блокуємо команду.
    asyncio.create_task(_wait_and_deliver(interaction, session_id, editor_url))
