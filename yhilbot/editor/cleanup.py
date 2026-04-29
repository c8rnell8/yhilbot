"""Фоновый цикл очистки истёкших сессий и старых файлов кэша."""
from __future__ import annotations

import asyncio
import os
import time

from .. import config
from ..logging_setup import log
from .db import delete_session, init_db
from .models import active_sessions


async def editor_cleanup_loop() -> None:
    await init_db()
    while True:
        try:
            await asyncio.sleep(config.CLEANUP_INTERVAL_SEC)
            now = time.time()

            # Истёкшие активные сессии
            expired = [
                mid for mid, s in list(active_sessions.items())
                if now - s.last_activity > config.EDITOR_TIMEOUT_SEC
            ]
            for mid in expired:
                sess = active_sessions.pop(mid, None)
                if sess:
                    if sess.render_task and not sess.render_task.done():
                        sess.cancel_flag.set()
                    if sess.input_path and os.path.exists(sess.input_path):
                        try:
                            os.remove(sess.input_path)
                        except Exception:
                            pass
                    await delete_session(mid)
                    log.info(f"🧹 Сессия {mid} истекла и удалена.")

            # Кэш-файлы старше TTL
            for cache_folder in (config.GIF_CACHE_DIR, config.CACHE_DIR):
                try:
                    for fname in os.listdir(cache_folder):
                        fpath = os.path.join(cache_folder, fname)
                        try:
                            if now - os.path.getmtime(fpath) > config.CACHE_TTL_SEC:
                                os.remove(fpath)
                        except Exception:
                            pass
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning(f"editor_cleanup_loop iteration: {e}")


def start_cleanup() -> None:
    asyncio.create_task(editor_cleanup_loop())
