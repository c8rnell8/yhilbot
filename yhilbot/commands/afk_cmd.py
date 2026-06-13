import discord

from .. import afk, config
from ..client import tree


@tree.command(name="afkconfig", description="Налаштувати авто-AFK роль (тільки власник)")
@discord.app_commands.describe(
    role="Роль, яку видавати неактивним",
    time="Період без активності: 30s, 15m, 12h, 30d, 2w, 3months (або просто число = дні)",
)
async def afkconfig_cmd(
    interaction: discord.Interaction,
    role: discord.Role,
    time: str = "30d",
) -> None:
    if interaction.user.id != config.OWNER_ID:
        await interaction.response.send_message("❌ Тільки для власника.", ephemeral=True)
        return
    if not interaction.guild:
        await interaction.response.send_message("Лише на сервері.", ephemeral=True)
        return

    seconds = afk.parse_duration(time)
    if seconds is None:
        await interaction.response.send_message(
            "Не зрозумів період. Приклади: `30s`, `15m`, `12h`, `30d`, `2w`, `3months`.",
            ephemeral=True,
        )
        return
    seconds = max(60, min(365 * 86400, seconds))

    me = interaction.guild.me
    if not me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "Мені потрібен дозвіл «Керувати ролями».", ephemeral=True
        )
        return
    if role >= me.top_role:
        await interaction.response.send_message(
            "Ця роль вища за мою — підніми мою роль вище неї в налаштуваннях сервера.",
            ephemeral=True,
        )
        return

    await afk.set_config(interaction.guild.id, role.id, seconds, True)
    await interaction.response.send_message(
        f"✅ Авто-AFK увімкнено. Роль {role.mention} видаватиметься після **{afk.format_duration(seconds)}** без активності "
        f"(повідомлення, реакції чи войс знімають її автоматично).",
        ephemeral=True,
    )


@tree.command(name="afkoff", description="Вимкнути авто-AFK (тільки власник)")
async def afkoff_cmd(interaction: discord.Interaction) -> None:
    if interaction.user.id != config.OWNER_ID:
        await interaction.response.send_message("❌ Тільки для власника.", ephemeral=True)
        return
    if not interaction.guild:
        return
    cfg = afk.get_config(interaction.guild.id)
    if not cfg:
        await interaction.response.send_message("Авто-AFK і так не налаштований.", ephemeral=True)
        return
    await afk.set_config(interaction.guild.id, cfg["role_id"], cfg["threshold"], False)
    await interaction.response.send_message("⏸️ Авто-AFK вимкнено.", ephemeral=True)


@tree.command(name="afklist", description="Список неактивних бійців (AFK)")
@discord.app_commands.describe(page="Сторінка списку (по 20 на сторінку)")
async def afklist_cmd(interaction: discord.Interaction, page: int = 1) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Лише на сервері.", ephemeral=True)
        return
    cfg = afk.get_config(interaction.guild.id)
    if not cfg:
        await interaction.response.send_message(
            "Авто-AFK не налаштований. Власник може ввімкнути через /afkconfig.",
            ephemeral=True,
        )
        return

    role = interaction.guild.get_role(cfg["role_id"])
    if not role:
        await interaction.response.send_message("AFK-роль видалено. Перенастрой /afkconfig.", ephemeral=True)
        return

    # Everyone who currently holds the AFK role, longest-idle first.
    members = [m for m in role.members if not m.bot]
    members.sort(
        key=lambda m: afk.inactivity_seconds(interaction.guild.id, m.id),
        reverse=True,
    )

    per_page = 20
    total = len(members)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    chunk = members[(page - 1) * per_page : page * per_page]

    if total == 0:
        await interaction.response.send_message("Зараз у AFK нікого немає 🎉", ephemeral=True)
        return

    lines = []
    for i, m in enumerate(chunk, start=(page - 1) * per_page + 1):
        dur = afk.format_duration(afk.inactivity_seconds(interaction.guild.id, m.id))
        lines.append(f"`{i:>3}.` {m.mention} — **{dur}**")

    embed = discord.Embed(
        title=f"💤 AFK — {total} бійців",
        description="\n".join(lines),
        color=0xFBBF24,
    )
    embed.set_footer(text=f"Сторінка {page}/{pages} · роль @{role.name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)
