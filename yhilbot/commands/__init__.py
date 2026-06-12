def register_all() -> None:
    # Importing each module registers its slash command as a side effect.
    from . import caption_cmd, edit_cmd, gif_cmd, help_cmd, stats_cmd  # noqa: F401
