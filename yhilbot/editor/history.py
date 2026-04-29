"""Undo/Redo с ограниченной историей."""
from __future__ import annotations

import asyncio

from .db import save_session
from .models import EditorSession, tl_from_dict, tl_to_dict

HISTORY_LIMIT = 25


def push_history(sess: EditorSession) -> None:
    """Запоминает текущее состояние таймлайна (после изменения)."""
    sess.history = sess.history[: sess.history_pos + 1]
    sess.history.append(tl_to_dict(sess.timeline))
    sess.history_pos = len(sess.history) - 1
    if len(sess.history) > HISTORY_LIMIT:
        sess.history.pop(0)
        sess.history_pos -= 1
    asyncio.create_task(save_session(sess))


def undo(sess: EditorSession) -> bool:
    if sess.history_pos > 0:
        sess.history_pos -= 1
        sess.timeline = tl_from_dict(sess.history[sess.history_pos])
        return True
    return False


def redo(sess: EditorSession) -> bool:
    if sess.history_pos < len(sess.history) - 1:
        sess.history_pos += 1
        sess.timeline = tl_from_dict(sess.history[sess.history_pos])
        return True
    return False
