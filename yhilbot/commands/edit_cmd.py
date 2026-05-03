"""/edit — запуск видеоредактора."""
from __future__ import annotations

import os

import discord
from discord import app_commands

from .. import config
from ..client import tree
from ..editor.db import (
    find_active_session_for_user,
    init_db,
    load_preset,
    load_session_by_share_code,
)
from ..editor.history import push_history
from ..editor.models import Clip, EditorSession, Timeline, active_sessions
from ..editor.view import EditorView, build_readonly_embed
from ..ffmpeg_helpers import get_video_duration
from ..logging_setup import log
from ..media_utils import get_media_from_context, safe_save


@tree.command(
    name="edit",
    description="QUAD видеоредактор с таймлайном, текстовыми наложениями и фоновым рендером",
)
@app_commands.describe(
    media="Видеофайл (до 100 МБ, до 5 мин)",
    join_code="Код сессии для просмотра (read-only)",
)
async def edit_cmd(
    interaction: discord.Interaction,
    media: discord.Attachment | None = None,
    join_code: str | None = None,
) -> None:
    await interaction.response.defer(thinking=True)
    await init_db()

    # ── Read-only просмотр чужой сессии по share_code ─────────────────────────
    if join_code:
        sess = await load_session_by_share_code(join_code)
        if not sess or not sess.input_path or not os.path.exists(sess.input_path):
            await interaction.followup.send("❌ Сессия не найдена или уже закрыта.", ephemeral=True)
            return
        # Для read-only НЕ передаём view — embed-снимок без интерактива.
        embed = build_readonly_embed(sess)
        await interaction.followup.send(embed=embed)
        return

    # ── Авто-восстановление активной сессии того же пользователя ──────────────
    # Сначала ищем живую сессию в памяти: у неё уже могут быть привязаны
    # render_task / cancel_flag / lock, и пересоздавать объект из БД нельзя —
    # потеряется связь с фоновым рендером и кнопкой 🛑.
    existing: EditorSession | None = None
    for sess_in_mem in active_sessions.values():
        if (
            sess_in_mem.user_id == interaction.user.id
            and sess_in_mem.channel_id == interaction.channel_id
            and sess_in_mem.input_path
            and os.path.exists(sess_in_mem.input_path)
        ):
            existing = sess_in_mem
            break
    if existing is None:
        # В памяти нет — пробуем поднять из БД (бот мог рестартовать).
        existing = await find_active_session_for_user(
            interaction.user.id, interaction.channel_id
        )
        if existing and (not existing.input_path or not os.path.exists(existing.input_path)):
            existing = None
    if existing is not None:
        old_mid = existing.message_id
        view = EditorView(existing)
        msg = await interaction.followup.send("🔄 Сессия восстановлена.", view=view)
        existing.channel = interaction.channel
        existing.message = msg
        existing.message_id = msg.id  # перепривязываем сессию к новому followup-сообщению
        # Заменить ключ в active_sessions: убрать старый mid и положить под новым.
        active_sessions.pop(old_mid, None)
        active_sessions[msg.id] = existing
        await view.update_ui("✅ Продолжайте с того места.")
        return

    # ── Новая сессия ──────────────────────────────────────────────────────────
    if not media:
        media = await get_media_from_context(interaction, content_filter=("video/",))
    if not media:
        await interaction.followup.send("❌ Видео не найдено.")
        return
    if not media.content_type or not media.content_type.startswith("video/"):
        await interaction.followup.send("❌ Поддерживаются только видеофайлы.")
        return
    if media.size > config.MAX_INPUT_MB * 1024 * 1024:
        await interaction.followup.send(f"❌ Файл > {config.MAX_INPUT_MB} МБ.")
        return

    ext = media.filename.rsplit(".", 1)[-1].lower() if "." in media.filename else "mp4"
    inp = os.path.join(config.TEMP_DIR, f"edit_i_{interaction.id}.{ext}")

    try:
        if not await safe_save(media, inp):
            await interaction.followup.send("❌ Не удалось скачать.")
            return
        duration = await get_video_duration(inp)
        if duration <= 0:
            await interaction.followup.send("❌ Не удалось прочитать длительность.")
            return
        if duration > config.MAX_VIDEO_SEC:
            await interaction.followup.send(f"❌ Видео > {config.MAX_VIDEO_SEC // 60} мин.")
            return

        tl = Timeline(clips=[Clip(source=inp, start=0.0, end=min(10.0, duration))])
        pset = await load_preset(interaction.user.id)
        if pset:
            tl.width = pset.get("width", 720)
            tl.fps = pset.get("fps", 15)
            tl.quality = pset.get("quality", 75)

        # Создаём сессию с временным message_id (interaction.id), потом перебиваем
        # на реальный ID followup-сообщения после .send(). push_history (и любую
        # запись в БД) откладываем до момента финализации message_id, иначе в БД
        # окажется orphaned-строка с ключом interaction.id.
        sess = EditorSession(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            message_id=interaction.id,
            input_path=inp,
            duration=duration,
            timeline=tl,
        )

        view = EditorView(sess)
        msg = await interaction.followup.send(
            f"🎬 QUAD Редактор {'(GPU 🟢 detected)' if config.GPU_AVAILABLE else '(CPU 🔵)'}",
            view=view,
        )
        sess.channel = interaction.channel
        sess.message = msg
        sess.message_id = msg.id  # ключуем именно по message id, а не interaction.id
        active_sessions[sess.message_id] = sess

        # Теперь, когда message_id указывает на реальное сообщение, можно сохранить
        # начальное состояние в БД через history.
        push_history(sess)

        await view.update_ui("Готово! ✂️ Split, 📝 Текст, ⏱️ Точно, ✅ Рендер.")

    except Exception as e:
        log.exception(f"Editor init [{interaction.user}]: {e}")
        if os.path.exists(inp):
            try:
                os.remove(inp)
            except Exception:
                pass
        if not interaction.is_expired():
            try:
                await interaction.followup.send("❌ Ошибка запуска редактора.")
            except Exception:
                pass
