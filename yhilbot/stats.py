"""Атомарные счётчики бота.

Заменяет голый `Dict[str, int]` из v5.1, где `BOT_STATS["x"] += 1` под несколькими
тасками не атомарен (load-modify-store).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class _Counters:
    gif_ok: int = 0
    gif_fail: int = 0
    caption_ok: int = 0
    caption_fail: int = 0
    edit_ok: int = 0
    edit_fail: int = 0


class BotStats:
    """Потокобезопасные счётчики + uptime."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._c = _Counters()
        self.start_time: float = time.time()

    def inc(self, name: str, delta: int = 1) -> None:
        with self._lock:
            setattr(self._c, name, getattr(self._c, name) + delta)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "gif_ok": self._c.gif_ok,
                "gif_fail": self._c.gif_fail,
                "caption_ok": self._c.caption_ok,
                "caption_fail": self._c.caption_fail,
                "edit_ok": self._c.edit_ok,
                "edit_fail": self._c.edit_fail,
            }


stats = BotStats()
