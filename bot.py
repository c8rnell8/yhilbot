from yhilbot import commands as _commands  # noqa: F401
from yhilbot import lifecycle as _lifecycle  # noqa: F401
from yhilbot.client import client
from yhilbot.config import TOKEN, validate_and_init_paths
from yhilbot.lifecycle import install_signal_handlers
from yhilbot.logging_setup import setup_logging


def main() -> None:
    validate_and_init_paths()
    setup_logging()
    _commands.register_all()
    install_signal_handlers()
    assert TOKEN is not None
    client.run(TOKEN)


if __name__ == "__main__":
    main()
