import hashlib
import json
import os
from typing import Any

from . import config


def cache_key(data: Any) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def cache_path(key: str, ext: str = "webp") -> str:
    return os.path.join(config.CACHE_DIR, f"{key}.{ext}")
