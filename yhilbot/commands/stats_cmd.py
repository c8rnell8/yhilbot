import os
import time

import discord
import psutil

from .. import config
from ..client import tree
from ..editor.models import active_sessions
from ..queue_mgr import queue_length
from ..stats import stats


@tree.command(name="stats", description="Статистика бота и сервера (только для владельца)")
async def stats_cmd(interaction: discord.Interaction) -> None:
    if interaction.user.id != config.OWNER_ID:
        await interaction.response.send_message("❌ Доступ ограничен.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)

    snap = stats.snapshot()
    uptime = time.time() - stats.start_time
    d, r = divmod(uptime, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    uptime_str = f"{int(d)}д {int(h)}ч {int(m)}м"

    qlen = queue_length()

    temp_mb = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fn in os.walk(config.TEMP_DIR)
        for f in fn if os.path.exists(os.path.join(dp, f))
    ) / 1024 / 1024
    log_mb = (
        os.path.getsize(config.LOG_PATH) / 1024 / 1024 if os.path.exists(config.LOG_PATH) else 0
    )

    cpu_pct: str = "N/A"
    mem_mb: str = "N/A"
    disk_str: str = "N/A"
    try:
        proc = psutil.Process(os.getpid())
        cpu_pct = f"{proc.cpu_percent(interval=None):.1f}%"
        mem_mb = f"{proc.memory_info().rss / 1024**2:.1f} МБ"
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        disk_str = f"{disk.used/1024**3:.1f}/{disk.total/1024**3:.1f} ГБ ({disk.percent}%)"
    except Exception:
        pass

    # NVENC is only detected for display; rendering always uses libwebp.
    gpu_str = (
        "✅ NVENC задетектен (но рендер использует libwebp)" if config.GPU_AVAILABLE
        else "❌ NVENC не задетектен"
    )
    await interaction.followup.send(
        f"📊 **Статистика yhilbot**\n"
        f"⏱️ Аптайм: `{uptime_str}` | 🖥️ GPU: {gpu_str}\n"
        f"🧵 Очередь: `{qlen}` | 📝 Активных сессий: `{len(active_sessions)}`\n\n"
        f"🎬 **Конвертации:**\n"
        f"GIF/WebP ✅`{snap['gif_ok']}` ❌`{snap['gif_fail']}` | "
        f"Caption ✅`{snap['caption_ok']}` ❌`{snap['caption_fail']}` | "
        f"Editor ✅`{snap['edit_ok']}` ❌`{snap['edit_fail']}`\n\n"
        f"💻 **Ресурсы:** CPU `{cpu_pct}` | RAM `{mem_mb}`\n"
        f"💾 Диск: `{disk_str}` | Temp: `{temp_mb:.1f} МБ` | Логи: `{log_mb:.1f} МБ`"
    )
