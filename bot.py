"""yhilbot — точка входа.

Все команды и события регистрируются на стороне `yhilbot` пакета через
import-side-effect. Этот файл — тонкий лаунчер.
"""
from __future__ import annotations

from yhilbot import commands as _commands  # noqa: F401  (регистрирует /gif, /caption, /edit, /stats, /help)
from yhilbot import lifecycle as _lifecycle  # noqa: F401  (регистрирует on_ready)
from yhilbot.client import client
from yhilbot.config import TOKEN, validate_and_init_paths
from yhilbot.lifecycle import install_signal_handlers
from yhilbot.logging_setup import setup_logging


def main() -> None:
    validate_and_init_paths()
    setup_logging()
    _commands.register_all()
    install_signal_handlers()
    assert TOKEN is not None  # validate_and_init_paths гарантирует
    client.run(TOKEN)


if __name__ == "__main__":
    main()
