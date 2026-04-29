"""Глобальный логгер."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from . import config

log = logging.getLogger("yhilbot")


def setup_logging() -> None:
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for h in (
        RotatingFileHandler(config.LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(),
    ):
        h.setFormatter(fmt)
        log.addHandler(h)
