from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import ui

from .history import push_history
from .models import EditorSession, Overlay

if TYPE_CHECKING:
    from .view import EditorView


def parse_time(raw: str) -> float | None:
    """Parse MM:SS.mmm or plain seconds (dot or comma decimal separator)."""
    raw = raw.strip().replace(",", ".")
    # MM:SS, with SS strictly < 60
    m = re.match(r"^(\d+):([0-5]\d)(?:\.(\d{1,3}))?$", raw)
    if m:
        mm = int(m.group(1))
        ss = int(m.group(2))
        ms = int((m.group(3) or "0").ljust(3, "0"))
        return mm * 60 + ss + ms / 1000
    if re.match(r"^\d+(?:\.\d{1,3})?$", raw):
        return float(raw)
    return None


class TimeModal(ui.Modal, title="⏱️ Точное время клипа"):
    start_in = ui.TextInput(
        label="Начало (MM:SS.mmm или сек)",
        placeholder="0:00.000 или 12.345",
        required=True, max_length=12,
    )
    end_in = ui.TextInput(
        label="Конец (MM:SS.mmm или сек)",
        placeholder="0:05.000 или 18.200",
        required=True, max_length=12,
    )

    def __init__(self, sess: EditorSession, view: EditorView) -> None:
        super().__init__()
        self.sess = sess
        self.view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        s = parse_time(self.start_in.value)
        e = parse_time(self.end_in.value)
        if s is None or e is None or s < 0 or e <= s or e > self.sess.duration:
            await interaction.response.send_message(
                "❌ Неверный формат или границы.", ephemeral=True
            )
            return
        async with self.sess.lock:
            if self.sess.timeline.clips:
                self.sess.timeline.clips[0].start = s
                self.sess.timeline.clips[0].end = e
            self.sess.timeline.cursor = s
            push_history(self.sess)
        await interaction.response.defer()
        await self.view.update_ui_from_modal(interaction, "✅ Время обновлено.")


class TextOverlayModal(ui.Modal, title="📝 Добавить текстовое наложение"):
    text_in = ui.TextInput(
        label="Текст", placeholder="HELLO WORLD",
        required=True, max_length=100,
    )
    start_in = ui.TextInput(
        label="Появляется (сек или MM:SS)", placeholder="0.0",
        required=True, max_length=12,
    )
    end_in = ui.TextInput(
        label="Исчезает (сек или MM:SS)", placeholder="3.0",
        required=True, max_length=12,
    )
    color_in = ui.TextInput(
        label="Цвет (white / yellow / red / #ff00aa / …)",
        placeholder="white",
        required=False, max_length=20,
    )

    def __init__(self, sess: EditorSession, view: EditorView) -> None:
        super().__init__()
        self.sess = sess
        self.view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        s = parse_time(self.start_in.value)
        e = parse_time(self.end_in.value)
        if s is None or e is None or e <= s:
            await interaction.response.send_message(
                "❌ Неверное время.", ephemeral=True
            )
            return
        # Color is sanitized at render time; just normalize to a white default here.
        color = (self.color_in.value or "white").strip().lower() or "white"
        async with self.sess.lock:
            self.sess.timeline.overlays.append(
                Overlay(text=self.text_in.value, start=s, end=e, color=color)
            )
            push_history(self.sess)
        await interaction.response.defer()
        await self.view.update_ui_from_modal(
            interaction, f"📝 Надпись добавлена: «{self.text_in.value}»"
        )
