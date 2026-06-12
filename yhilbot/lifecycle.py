import asyncio
import atexit
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
                    log.warning(f"sync failed for {gid}: {e}")
            log.info(f"commands synced on {ok}/{len(config.GUILD_IDS)} guilds")
        else:
            await tree.sync()
            log.info("global sync (propagates in 15-60 min)")
    except Exception as e:
        log.error(f"sync error: {e}")

    log.info(
        f"ready: {client.user} | "
        f"GPU={'NVENC detected' if config.GPU_AVAILABLE else 'no'} | "
        f"GUILD_IDS={config.GUILD_IDS or 'global'}"
    )


_cleaned_up = False


def _sync_cleanup() -> None:
    global _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    for _mid, sess in list(active_sessions.items()):
        if sess.input_path and os.path.exists(sess.input_path):
            try:
                os.remove(sess.input_path)
            except Exception:
                pass
    if os.path.exists(config.TEMP_DIR):
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
    db_shutdown()


async def _async_shutdown() -> None:
    log.info("shutting down...")
    for _mid, sess in list(active_sessions.items()):
        if sess.render_task and not sess.render_task.done():
            sess.cancel_flag.set()
    _sync_cleanup()
    try:
        await client.close()
    except Exception:
        pass


def install_signal_handlers() -> None:
    # discord.py closes the client itself on Ctrl-C / SIGTERM (it owns the
    # event loop). We just make sure temp files and the db get cleaned up when
    # the interpreter exits - this works on both Windows and Linux. Where a
    # running loop is available (Unix), also hook the signals for a tidier
    # async shutdown.
    atexit.register(_sync_cleanup)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_async_shutdown()))
        except (NotImplementedError, RuntimeError):
            pass
