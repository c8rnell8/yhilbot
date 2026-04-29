"""Лайфсайкл бота: on_ready и graceful shutdown."""
from __future__ import annotations

import asyncio
import os
import shutil
import signal

import discord
import psutil

from . import config
from .client import client, tree
from .editor.cleanup import start_cleanup
from .editor.db import init_db
from .editor.db import shutdown as db_shutdown
from .editor.models import active_sessions
from .ffmpeg_helpers import detect_gpu
from .logging_setup import log


@client.event
async def on_ready() -> None:
    config.set_gpu_available(await detect_gpu())
    try:
        psutil.Process(os.getpid()).cpu_percent(interval=None)
    except Exception:
        pass

    start_cleanup()
    await init_db()

    try:
        if config.GUILD_IDS:
            ok = 0
            for gid in config.GUILD_IDS:
                try:
                    await tree.sync(guild=discord.Object(id=gid))
                    ok += 1
                except Exception as e:
                    log.warning(f"Sync failed для {gid}: {e}")
            log.info(f"✅ Команды синхронизированы на {ok}/{len(config.GUILD_IDS)} серверах")
        else:
            await tree.sync()
            log.info("✅ Глобальная синхронизация (обновление 15–60 мин)")
    except Exception as e:
        log.error(f"Sync error: {e}")

    log.info(
        f"🟢 Готов: {client.user} | "
        f"GPU={'NVENC detected' if config.GPU_AVAILABLE else 'нет'} | "
        f"GUILD_IDS={config.GUILD_IDS or 'global'}"
    )


async def _async_shutdown() -> None:
    log.info("🛑 Завершение работы...")
    for _mid, sess in list(active_sessions.items()):
        if sess.render_task and not sess.render_task.done():
            sess.cancel_flag.set()
        if sess.input_path and os.path.exists(sess.input_path):
            try:
                os.remove(sess.input_path)
            except Exception:
                pass
    if os.path.exists(config.TEMP_DIR):
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
    db_shutdown()
    try:
        await client.close()
    except Exception:
        pass


def install_signal_handlers() -> None:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_async_shutdown()))
        except (NotImplementedError, RuntimeError):
            # Windows / loop ещё не запущен — fallback на sync handler.
            signal.signal(sig, lambda *_: asyncio.run(_async_shutdown()))
