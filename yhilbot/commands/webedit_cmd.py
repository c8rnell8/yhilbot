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


async def _notify(
    interaction: discord.Interaction,
    *,
    content: str,
    payload: bytes | None = None,
    filename: str | None = None,
    ephemeral: bool = False,
) -> bool:
    """Best-effort notification: prefer channel.send, fall back to followup.

    Discord interaction-tokens expire after ~15 min, but our poll loop runs
    up to WEB_EDITOR_TIMEOUT_SEC (default 30 min). После 15 хв
    `interaction.followup.send` падає з 401 — для довгих рендерів треба
    писати у канал безпосередньо. Pings the user explicitly so they still get
    a notification even when the message isn't a reply.

    File handling: takes raw bytes + filename instead of a pre-built
    `discord.File`, because discord.py consumes the underlying BytesIO on
    each send (the stream position ends at EOF and a second call would
    transmit 0 bytes). We construct a fresh `discord.File` per send attempt.

    Returns True if at least one send succeeded, False if both paths failed
    (e.g. file too large for both channel and followup, or token expired
    AND no channel access). Caller should use this to drive a fallback
    such as posting just a download link.
    """
    has_file = payload is not None and filename is not None

    def _fresh_file() -> discord.File | None:
        if not has_file:
            return None
        return discord.File(io.BytesIO(payload), filename=filename)  # type: ignore[arg-type]

    channel = interaction.channel
    can_channel = channel is not None and hasattr(channel, "send") and not ephemeral
    last_exc: discord.HTTPException | None = None
    if can_channel:
        try:
            f = _fresh_file()
            if f is not None:
                await channel.send(content=content, file=f)  # type: ignore[union-attr]
            else:
                await channel.send(content=content)  # type: ignore[union-attr]
            return True
        except discord.HTTPException as e:
            log.warning("webedit:channel_send_failed err=%s", e)
            last_exc = e
    # Fallback на followup — працює тільки в перші 15 хв.
    try:
        f = _fresh_file()
        if f is not None:
            await interaction.followup.send(content=content, file=f, ephemeral=ephemeral)
        else:
            await interaction.followup.send(content=content, ephemeral=ephemeral)
        return True
    except discord.HTTPException as e:
        log.warning(
            "webedit:followup_send_failed err=%s (token may be expired)", e
        )
        last_exc = e
    log.warning(
        "webedit:notify_all_paths_failed last_err=%s (file=%s)",
        last_exc,
        "yes" if has_file else "no",
    )
    return False


async def _wait_and_deliver(
    interaction: discord.Interaction, session_id: str, editor_url: str
) -> None:
    """Поллим сайт, при каждом завершённом рендере постим результат в канал.

    The site now exposes a monotonic `renderGen` counter on the session,
    which ticks on every successful render completion. We track the last
    generation we delivered so that a single /webedit session can produce
    multiple renders — user iterates in the web editor and each click on
    "Готово" sends a fresh result message into the channel.

    We keep polling until `WEB_EDITOR_TIMEOUT_SEC` elapses, the session is
    explicitly closed, or a render transitions to `failed`. The timer is
    idle-based: it resets whenever a new render finishes, so long editing
    sessions don't get cut off mid-iteration.

    Wrapped in a top-level try/except — это fire-and-forget таска,
    необроблені виключення тут просто логуються.
    """
    timeout = aiohttp.ClientTimeout(total=config.WEB_EDITOR_TIMEOUT_SEC + 60)
    started = time.time()
    deadline = started + config.WEB_EDITOR_TIMEOUT_SEC
    last_status: str | None = None
    last_gen: int = 0
    last_render_failed_gen: int = -1

    try:
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

                gen = int(data.get("renderGen") or 0)

                if status == "rendered" and gen > last_gen:
                    output = data.get("output") or {}
                    ext = output.get("ext") or ".mp4"
                    try:
                        payload = await _download_output(session, session_id)
                    except Exception as e:
                        log.error("webedit:download_failed session=%s gen=%s err=%s", session_id, gen, e)
                        await _notify(
                            interaction,
                            content=(
                                f"<@{interaction.user.id}> ❌ Готовий рендер з "
                                f"[веб-редактора]({editor_url}) не вдалося завантажити: {e}"
                            ),
                        )
                        last_gen = gen
                        # Reset idle deadline so user has full window to try again.
                        deadline = time.time() + config.WEB_EDITOR_TIMEOUT_SEC
                        await asyncio.sleep(config.WEB_EDITOR_POLL_SEC)
                        continue

                    prefix = "✓ Готово" if last_gen == 0 else f"↻ Новий рендер (#{gen})"
                    content = (
                        f"<@{interaction.user.id}> {prefix} — з "
                        f"[веб-редактора]({editor_url})."
                    )
                    sent = await _notify(
                        interaction,
                        content=content,
                        payload=payload,
                        filename=f"yhilbot-{session_id}-v{gen}{ext}",
                    )
                    if not sent:
                        log.warning(
                            "webedit:send_with_file_failed_fallback_to_link session=%s gen=%s",
                            session_id,
                            gen,
                        )
                        download_url = (
                            f"{config.WEB_EDITOR_URL}/api/editor/sessions/{session_id}/output?dl=1"
                        )
                        await _notify(
                            interaction,
                            content=(
                                f"<@{interaction.user.id}> {prefix}, але файл завеликий "
                                f"для каналу. Завантаж напряму: {download_url}"
                            ),
                        )
                    last_gen = gen
                    # Idle-based deadline: extend to full window on each new render.
                    deadline = time.time() + config.WEB_EDITOR_TIMEOUT_SEC

                elif status == "failed" and gen > last_render_failed_gen:
                    # A render attempt failed. Tell the user but keep polling —
                    # they may try again in the editor. Note: render.ts only
                    # bumps renderGen on success, so a failed render increments
                    # updatedAt without bumping gen. We trigger once per status
                    # transition by tracking the bump we alerted on.
                    err = data.get("error") or "unknown"
                    await _notify(
                        interaction,
                        content=(
                            f"<@{interaction.user.id}> ❌ Рендер з "
                            f"[веб-редактора]({editor_url}) впав: `{str(err)[:300]}`"
                            f"\nМожеш спробувати ще раз там же, я почекаю."
                        ),
                    )
                    last_render_failed_gen = gen

                await asyncio.sleep(config.WEB_EDITOR_POLL_SEC)

            # ── Таймаут idle (>WEB_EDITOR_TIMEOUT_SEC с моменту останнього рендера) ─
            if last_gen == 0:
                tail = (
                    f"⏱ Час очікування рендера вийшов "
                    f"({config.WEB_EDITOR_TIMEOUT_SEC}s). "
                    f"Якщо ще не натиснув «Готово» — натисни тут: {editor_url}"
                )
            else:
                tail = (
                    f"⏱ Сесія веб-редактора закрита через неактивність "
                    f"(отримано {last_gen} рендер(ів)). "
                    f"Хочеш ще — виклич /webedit знову."
                )
            await _notify(
                interaction,
                content=f"<@{interaction.user.id}> {tail}",
            )
    except Exception as e:
        # Останній рубіж захисту: ніколи не пропускаємо у asyncio "Task exception was never retrieved".
        log.exception("webedit:wait_and_deliver crashed session=%s err=%s", session_id, e)


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
