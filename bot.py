import os
import sys

import discord

from yhilbot import commands as _commands  # noqa: F401
from yhilbot import lifecycle as _lifecycle  # noqa: F401
from yhilbot.client import client
from yhilbot.config import TOKEN, validate_and_init_paths
from yhilbot.lifecycle import install_signal_handlers
from yhilbot.logging_setup import setup_logging
from yhilbot.logging_setup import log


def main() -> None:
    validate_and_init_paths()
    setup_logging()
    _commands.register_all()
    install_signal_handlers()
    assert TOKEN is not None
    try:
        client.run(TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        # The "Server Members Intent" toggle isn't enabled in the Developer
        # Portal yet. Rather than stay offline, relaunch once without that
        # intent so all the other commands keep working; AFK auto-role turns
        # on by itself once the toggle is enabled and the bot is restarted.
        if os.environ.get("YHIL_NO_MEMBERS") == "1":
            raise
        log.warning(
            "Server Members Intent is OFF in the Developer Portal — restarting "
            "without it. Enable it at discord.com/developers and restart for AFK."
        )
        os.environ["YHIL_NO_MEMBERS"] = "1"
        os.execv(sys.executable, [sys.executable, *sys.argv])


if __name__ == "__main__":
    main()
