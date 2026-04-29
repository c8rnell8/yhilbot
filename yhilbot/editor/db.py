"""SQLite-хранилище сессий и пресетов.

ВАЖНО: соединение хранится thread-local (один conn на воркер ThreadPoolExecutor),
чтобы избежать overhead'а на повторный connect/close.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import sqlite3
import threading
from typing import Any

from .. import config
from ..logging_setup import log
from .models import EditorSession, _new_share_code, tl_from_dict, tl_to_dict

_db_local = threading.local()
_db_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="yhil-db")
_db_initialized = False
_db_init_lock = asyncio.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_db_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _db_local.conn = conn
    return conn


async def db_exec(query: str, params: tuple = (), fetch: bool = False) -> Any:
    def _run():
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return None

    return await asyncio.get_running_loop().run_in_executor(_db_executor, _run)


async def init_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    async with _db_init_lock:
        if _db_initialized:
            return
        await db_exec("""
            CREATE TABLE IF NOT EXISTS sessions (
                message_id    INTEGER PRIMARY KEY,
                user_id       INTEGER,
                channel_id    INTEGER,
                input_path    TEXT,
                duration      REAL,
                timeline_json TEXT,
                history_json  TEXT,
                history_pos   INTEGER,
                last_activity REAL,
                share_code    TEXT UNIQUE
            )
        """)
        await db_exec("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_chan
            ON sessions(user_id, channel_id, last_activity)
        """)
        await db_exec("""
            CREATE TABLE IF NOT EXISTS presets (
                user_id       INTEGER PRIMARY KEY,
                settings_json TEXT
            )
        """)
        _db_initialized = True


async def save_session(sess: EditorSession) -> None:
    """Идемпотентное сохранение. При коллизии share_code генерирует новый."""
    for _ in range(3):
        try:
            await db_exec(
                "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    sess.message_id, sess.user_id, sess.channel_id,
                    sess.input_path, sess.duration,
                    json.dumps(tl_to_dict(sess.timeline)),
                    json.dumps(sess.history),
                    sess.history_pos, sess.last_activity,
                    sess.share_code,
                ),
            )
            return
        except sqlite3.IntegrityError:
            log.warning("save_session: share_code collision, regenerating...")
            sess.share_code = _new_share_code()
        except Exception as e:
            log.warning(f"save_session: {e}")
            return


def _row_to_session(r: tuple) -> EditorSession:
    return EditorSession(
        message_id=r[0], user_id=r[1], channel_id=r[2],
        input_path=r[3], duration=r[4],
        timeline=tl_from_dict(json.loads(r[5])),
        history=json.loads(r[6]),
        history_pos=r[7], last_activity=r[8], share_code=r[9],
    )


async def load_session(message_id: int) -> EditorSession | None:
    try:
        rows = await db_exec("SELECT * FROM sessions WHERE message_id=?", (message_id,), fetch=True)
        return _row_to_session(rows[0]) if rows else None
    except Exception as e:
        log.warning(f"load_session: {e}")
        return None


async def load_session_by_share_code(code: str) -> EditorSession | None:
    try:
        rows = await db_exec(
            "SELECT * FROM sessions WHERE share_code=?", (code.upper(),), fetch=True
        )
        return _row_to_session(rows[0]) if rows else None
    except Exception as e:
        log.warning(f"load_session_by_share_code: {e}")
        return None


async def find_active_session_for_user(user_id: int, channel_id: int) -> EditorSession | None:
    """Ищет последнюю по активности сессию пользователя в этом канале.

    Заменяет сломанную в v5.1 логику восстановления по `interaction.id`.
    """
    try:
        rows = await db_exec(
            "SELECT * FROM sessions WHERE user_id=? AND channel_id=? "
            "ORDER BY last_activity DESC LIMIT 1",
            (user_id, channel_id), fetch=True,
        )
        return _row_to_session(rows[0]) if rows else None
    except Exception as e:
        log.warning(f"find_active_session_for_user: {e}")
        return None


async def delete_session(message_id: int) -> None:
    try:
        await db_exec("DELETE FROM sessions WHERE message_id=?", (message_id,))
    except Exception:
        pass


async def save_preset(user_id: int, settings: dict) -> None:
    try:
        await db_exec(
            "INSERT OR REPLACE INTO presets VALUES (?,?)",
            (user_id, json.dumps(settings)),
        )
    except Exception as e:
        log.warning(f"save_preset: {e}")


async def load_preset(user_id: int) -> dict | None:
    try:
        rows = await db_exec(
            "SELECT settings_json FROM presets WHERE user_id=?", (user_id,), fetch=True
        )
        return json.loads(rows[0][0]) if rows else None
    except Exception:
        return None


def shutdown() -> None:
    """Закрыть БД-исполнитель и соединения."""
    _db_executor.shutdown(wait=False)
