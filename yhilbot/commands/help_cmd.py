"""/help — список команд."""
from __future__ import annotations

import discord

from .. import config
from ..client import tree


@tree.command(name="help", description="Список команд бота")
async def help_cmd(interaction: discord.Interaction) -> None:
    embed = discord.Embed(title="🎬 yhilbot — помощь", color=discord.Color.blurple())
    embed.add_field(
        name="/gif [media]",
        value=(
            "Конвертирует видео → WebP-анимацию, изображение → GIF.\n"
            "Если `media` не указан — берётся из последних сообщений канала."
        ),
        inline=False,
    )
    embed.add_field(
        name="/caption <text> [media]",
        value="Добавляет мем-заголовок шрифтом Impact поверх изображения.",
        inline=False,
    )
    embed.add_field(
        name="/edit [media] [join_code]",
        value=(
            "QUAD видеоредактор с таймлайном:\n"
            "• ✂️ Split — разрезать клип по курсору\n"
            "• 📝 Текст — наложить надпись (время, цвет)\n"
            "• ⚡ Скорость / 📐 Разрешение / 🎞️ FPS\n"
            "• ↩️ Undo / ↪️ Redo / 🛑 Стоп / ✅ Рендер\n"
            "• `join_code` — посмотреть чужую сессию (read-only embed)"
        ),
        inline=False,
    )
    embed.add_field(name="/stats", value="Статистика бота (только для владельца).", inline=False)
    embed.set_footer(
        text=(
            f"Лимит файла: {config.MAX_INPUT_MB} МБ | "
            f"Видео: до {config.MAX_VIDEO_SEC // 60} мин | "
            f"Вывод: ≤{config.OUTPUT_LIMIT_MB} МБ"
        )
    )
    await interaction.response.send_message(embed=embed)
