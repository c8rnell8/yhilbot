"""Регистрация всех slash-команд."""
from __future__ import annotations


def register_all() -> None:
    """Импортирует все модули команд — каждый из них регистрирует свою команду."""
    from . import caption_cmd, edit_cmd, gif_cmd, help_cmd, stats_cmd  # noqa: F401
