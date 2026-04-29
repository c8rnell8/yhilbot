"""UI редактора: кнопки, селекты, embed-обновление."""
from __future__ import annotations

import asyncio
import io
import time

import discord
from discord import ui

from .. import config
from ..logging_setup import log
from .db import delete_session, save_session
from .history import push_history, redo, undo
from .modals import TextOverlayModal, TimeModal
from .models import Clip, EditorSession, Timeline, active_sessions
from .preview import extract_dominant_color, gen_preview_frame
from .render import background_render, check_resources


def _fmt(sec: float) -> str:
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m):02d}:{s:05.2f}"


def predict_size_mb(tl: Timeline) -> float:
    """Грубая оценка размера итогового webp по эмпирической формуле."""
    total_dur = (
        sum(max(0.01, (c.end - c.start) / max(0.1, c.speed)) for c in tl.clips)
        if tl.clips else 0.01
    )
    # 0.16 — эмпирический коэффициент libwebp при quality~75 и base 720p/15fps.
    return max(0.3, total_dur * tl.fps * ((tl.width / 720) ** 2) * (tl.quality / 75) * 0.16)


class EditorView(ui.View):
    """View владельца сессии (с кнопками).

    Read-only режим (`/edit join_code=…`) показывается БЕЗ view — отдельным embed'ом.
    Это решает баг v5.1, где `_check_owner` блокировал ВСЕ кнопки чужому юзеру,
    превращая «read-only» в «no-access».
    """

    def __init__(self, sess: EditorSession) -> None:
        super().__init__(timeout=None)
        self.sess = sess
        self._last_edit = 0.0

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.sess.user_id:
            try:
                await interaction.response.send_message(
                    "❌ Это не ваша сессия.", ephemeral=True
                )
            except discord.InteractionResponded:
                pass
            return False
        return True

    # ─── Edit message helpers ─────────────────────────────────────────────────
    async def _edit_session_message(self, **kwargs) -> None:
        """Редактирует сообщение редактора через сохранённую ссылку.

        Это нужно, потому что `interaction.edit_original_response()` для модального
        submit редактирует МОДАЛЬНЫЙ deferred response, а не сообщение редактора.
        """
        msg = self.sess.message
        if msg is None:
            log.warning("_edit_session_message: sess.message is None")
            return
        try:
            await msg.edit(**kwargs)
        except discord.HTTPException as e:
            log.warning(f"_edit_session_message: {e}")

    async def _safe_edit(self, **kwargs) -> None:
        """Rate-limit редактирования сообщения до ~1 раза в 1.5 с."""
        wait = max(0.0, 1.5 - (time.time() - self._last_edit))
        if wait:
            await asyncio.sleep(wait)
        self._last_edit = time.time()
        await self._edit_session_message(**kwargs)

    # ─── Render UI snapshot ───────────────────────────────────────────────────
    async def _build_embed(self, note: str = "") -> tuple[discord.Embed, bytes | None]:
        tl = self.sess.timeline
        clip = tl.clips[0] if tl.clips else None
        dur = max(0.1, (clip.end - clip.start) / max(0.1, clip.speed)) if clip else 0.1
        pred = predict_size_mb(tl)
        pct = min(1.0, pred / config.OUTPUT_LIMIT_MB)
        bar = "█" * int(pct * 12) + "░" * (12 - int(pct * 12))
        color = (
            discord.Color.green() if pred < 20
            else discord.Color.orange() if pred < config.OUTPUT_LIMIT_MB
            else discord.Color.red()
        )
        frame = await gen_preview_frame(self.sess)
        if frame:
            color = await extract_dominant_color(frame)

        embed = discord.Embed(title="🎬 Видеоредактор QUAD", color=color)
        if clip:
            embed.add_field(
                name="⏱️ Текущий клип",
                value=f"`{_fmt(clip.start)} → {_fmt(clip.end)}` | `{dur:.2f}s` @ `{clip.speed}x`",
                inline=False,
            )
        embed.add_field(
            name="📐 Настройки",
            value=f"`{tl.width}p` | `{tl.fps} FPS` | `Q:{tl.quality}`",
            inline=True,
        )
        embed.add_field(name="🖱️ Курсор", value=f"`{_fmt(tl.cursor)}`", inline=True)
        embed.add_field(
            name="💾 Прогноз размера",
            value=f"{bar} `~{pred:.1f} МБ` {'✅' if pred < (config.OUTPUT_LIMIT_MB - 1) else '⚠️'}",
            inline=False,
        )
        if tl.overlays:
            embed.add_field(
                name=f"📝 Текстов: {len(tl.overlays)}",
                value=", ".join(f"«{ov.text}»" for ov in tl.overlays[:4]),
                inline=False,
            )
        if len(tl.clips) > 1:
            embed.add_field(name="✂️ Клипов", value=f"`{len(tl.clips)}` сегментов", inline=True)
        embed.add_field(name="🔗 Код шаринга", value=f"`{self.sess.share_code}`", inline=True)
        if note:
            embed.add_field(name="ℹ️", value=note, inline=False)
        embed.set_footer(
            text=(
                f"{'🟢 GPU detected' if config.GPU_AVAILABLE else '🔵 CPU'} | "
                f"История: {self.sess.history_pos + 1}/{len(self.sess.history)} | "
                f"Таймаут {config.EDITOR_TIMEOUT_SEC // 60} мин"
            )
        )
        return embed, frame

    async def update_ui(self, note: str = "") -> None:
        """Перерисовка embed редактора. Вызывается ТОЛЬКО после locked-мутации."""
        async with self.sess.lock:
            self.sess.last_activity = time.time()
            embed, frame = await self._build_embed(note)

        kwargs: dict = {"embed": embed, "view": self}
        if frame:
            kwargs["attachments"] = [discord.File(io.BytesIO(frame), filename="preview.jpg")]
        else:
            kwargs["attachments"] = []
        await self._safe_edit(**kwargs)
        asyncio.create_task(save_session(self.sess))

    async def update_ui_from_modal(
        self, modal_interaction: discord.Interaction, note: str = ""
    ) -> None:
        """То же что update_ui, но не использует interaction-привязанные API.

        Модальный submit-interaction уже defer'нут; редактируем сообщение
        редактора напрямую через self.sess.message.edit().
        """
        await self.update_ui(note)

    # ── Row 0: курсор + модалы ────────────────────────────────────────────────
    @ui.button(label="◀ -1s", style=discord.ButtonStyle.secondary, row=0,
               custom_id="yhil:editor:cursor:-1")
    async def b_minus_1(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            tl = self.sess.timeline
            clip = tl.clips[0] if tl.clips else None
            if clip:
                tl.cursor = max(clip.start, tl.cursor - 1.0)
            push_history(self.sess)
        await self.update_ui()

    @ui.button(label="📝 Точно", style=discord.ButtonStyle.primary, row=0,
               custom_id="yhil:editor:modal:time")
    async def b_time_modal(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.send_modal(TimeModal(self.sess, self))

    @ui.button(label="📝 Текст", style=discord.ButtonStyle.secondary, row=0,
               custom_id="yhil:editor:modal:text")
    async def b_text_modal(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.send_modal(TextOverlayModal(self.sess, self))

    @ui.button(label="▶ +1s", style=discord.ButtonStyle.secondary, row=0,
               custom_id="yhil:editor:cursor:+1")
    async def b_plus_1(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            tl = self.sess.timeline
            clip = tl.clips[0] if tl.clips else None
            if clip:
                tl.cursor = min(clip.end, tl.cursor + 1.0)
            push_history(self.sess)
        await self.update_ui()

    @ui.button(label="⏩ +5s", style=discord.ButtonStyle.secondary, row=0,
               custom_id="yhil:editor:cursor:+5")
    async def b_plus_5(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            tl = self.sess.timeline
            clip = tl.clips[0] if tl.clips else None
            if clip:
                tl.cursor = min(clip.end, tl.cursor + 5.0)
            push_history(self.sess)
        await self.update_ui()

    # ── Row 1: скорость ───────────────────────────────────────────────────────
    @ui.select(
        placeholder="⚡ Скорость", row=1, custom_id="yhil:editor:select:speed",
        options=[
            discord.SelectOption(label="0.5x — Slow-Mo", value="0.5"),
            discord.SelectOption(label="1.0x — Оригинал", value="1.0", default=True),
            discord.SelectOption(label="1.5x", value="1.5"),
            discord.SelectOption(label="2.0x — Timelapse", value="2.0"),
        ],
    )
    async def s_speed(self, i: discord.Interaction, s: ui.Select) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            if self.sess.timeline.clips:
                self.sess.timeline.clips[0].speed = float(s.values[0])
            push_history(self.sess)
        await self.update_ui()

    # ── Row 2: разрешение ─────────────────────────────────────────────────────
    @ui.select(
        placeholder="📐 Разрешение", row=2, custom_id="yhil:editor:select:scale",
        options=[
            discord.SelectOption(label="480p", value="480"),
            discord.SelectOption(label="640p", value="640"),
            discord.SelectOption(label="720p", value="720", default=True),
            discord.SelectOption(label="960p", value="960"),
            discord.SelectOption(label="1280p", value="1280"),
        ],
    )
    async def s_scale(self, i: discord.Interaction, s: ui.Select) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            self.sess.timeline.width = int(s.values[0])
            push_history(self.sess)
        await self.update_ui()

    # ── Row 3: FPS ────────────────────────────────────────────────────────────
    @ui.select(
        placeholder="🎞️ FPS", row=3, custom_id="yhil:editor:select:fps",
        options=[
            discord.SelectOption(label="8 FPS", value="8"),
            discord.SelectOption(label="12 FPS", value="12"),
            discord.SelectOption(label="15 FPS", value="15", default=True),
            discord.SelectOption(label="20 FPS", value="20"),
            discord.SelectOption(label="24 FPS", value="24"),
        ],
    )
    async def s_fps(self, i: discord.Interaction, s: ui.Select) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            self.sess.timeline.fps = int(s.values[0])
            push_history(self.sess)
        await self.update_ui()

    # ── Row 4: действия ───────────────────────────────────────────────────────
    @ui.button(label="✅ Рендер", style=discord.ButtonStyle.green, row=4,
               custom_id="yhil:editor:action:render")
    async def b_render(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer(thinking=True)
        ok, msg = await check_resources()
        if not ok:
            await i.followup.send(msg, ephemeral=True)
            return
        async with self.sess.lock:
            if not self.sess.timeline.clips:
                await i.followup.send("❌ Нет клипов в таймлайне.")
                return
            if self.sess.render_task and not self.sess.render_task.done():
                await i.followup.send("⏳ Рендер уже идёт.", ephemeral=True)
                return
            self.sess.render_task = asyncio.create_task(background_render(self.sess, i))
        await i.followup.send("🚀 Рендер запущен. Прогресс появится в канале.")

    @ui.button(label="✂️ Split", style=discord.ButtonStyle.secondary, row=4,
               custom_id="yhil:editor:action:split")
    async def b_split(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            tl = self.sess.timeline
            if not tl.clips:
                await i.followup.send("❌ Нет клипов.", ephemeral=True)
                return
            c = tl.clips[0]
            t = tl.cursor
            if not (c.start < t < c.end):
                await i.followup.send(
                    f"❌ Курсор `{_fmt(t)}` вне клипа `{_fmt(c.start)}–{_fmt(c.end)}`.",
                    ephemeral=True,
                )
                return
            before = Clip(c.source, c.start, t, c.speed, list(c.effects))
            after = Clip(c.source, t, c.end, c.speed, list(c.effects))
            tl.clips[0:1] = [before, after]
            push_history(self.sess)
        await self.update_ui(f"✂️ Клип разрезан в `{_fmt(t)}`")

    @ui.button(label="↩️ Undo", style=discord.ButtonStyle.secondary, row=4,
               custom_id="yhil:editor:action:undo")
    async def b_undo(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            success = undo(self.sess)
        if success:
            await self.update_ui("↩️ Отменено")
        else:
            await i.followup.send("ℹ️ Нет действий для отмены.", ephemeral=True)

    @ui.button(label="↪️ Redo", style=discord.ButtonStyle.secondary, row=4,
               custom_id="yhil:editor:action:redo")
    async def b_redo(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        async with self.sess.lock:
            success = redo(self.sess)
        if success:
            await self.update_ui("↪️ Возвращено")
        else:
            await i.followup.send("ℹ️ Нет действий для повтора.", ephemeral=True)

    @ui.button(label="🛑 Стоп", style=discord.ButtonStyle.red, row=4,
               custom_id="yhil:editor:action:stop")
    async def b_stop(self, i: discord.Interaction, b: ui.Button) -> None:
        if not await self._check_owner(i):
            return
        await i.response.defer()
        if self.sess.render_task and not self.sess.render_task.done():
            self.sess.cancel_flag.set()
            await i.followup.send("🛑 Отмена рендера отправлена.", ephemeral=True)
            return
        active_sessions.pop(self.sess.message_id, None)
        await delete_session(self.sess.message_id)
        if self.sess.input_path and self.sess.input_path.startswith(config.TEMP_DIR):
            try:
                import os
                if os.path.exists(self.sess.input_path):
                    os.remove(self.sess.input_path)
            except Exception:
                pass
        await self._safe_edit(content="🗑️ Редактор закрыт.", embed=None, attachments=[], view=None)


def build_readonly_embed(sess: EditorSession) -> discord.Embed:
    """Embed-снимок чужой сессии для read-only просмотра по `join_code`.

    Без кнопок — это снимок, а не интерактивный редактор.
    """
    tl = sess.timeline
    clip = tl.clips[0] if tl.clips else None
    pred = predict_size_mb(tl)
    embed = discord.Embed(
        title=f"👁️ Просмотр сессии `{sess.share_code}` (read-only)",
        color=discord.Color.greyple(),
    )
    if clip:
        dur = max(0.1, (clip.end - clip.start) / max(0.1, clip.speed))
        embed.add_field(
            name="⏱️ Клип",
            value=f"`{_fmt(clip.start)} → {_fmt(clip.end)}` | `{dur:.2f}s` @ `{clip.speed}x`",
            inline=False,
        )
    embed.add_field(
        name="📐", value=f"`{tl.width}p` | `{tl.fps} FPS` | `Q:{tl.quality}`", inline=True
    )
    embed.add_field(name="💾", value=f"~{pred:.1f} МБ", inline=True)
    if tl.overlays:
        embed.add_field(
            name=f"📝 Текстов: {len(tl.overlays)}",
            value=", ".join(f"«{ov.text}»" for ov in tl.overlays[:4]),
            inline=False,
        )
    if len(tl.clips) > 1:
        embed.add_field(name="✂️", value=f"`{len(tl.clips)}` клипов", inline=True)
    embed.set_footer(
        text=f"Только просмотр. Владелец: <@{sess.user_id}>"
    )
    return embed
