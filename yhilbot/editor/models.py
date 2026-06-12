import asyncio
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any


def _new_share_code() -> str:
    # 8 chars, no ambiguous symbols (no 0/O, 1/I, _/-).
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


@dataclass
class Effect:
    name: str
    params: dict = field(default_factory=dict)


@dataclass
class Clip:
    source: str
    start: float
    end: float
    speed: float = 1.0
    effects: list[Effect] = field(default_factory=list)


@dataclass
class Overlay:
    text: str
    start: float
    end: float
    x: str = "(w-text_w)/2"
    y: str = "50"
    size: int = 40
    color: str = "white"


@dataclass
class Timeline:
    clips: list[Clip] = field(default_factory=list)
    overlays: list[Overlay] = field(default_factory=list)
    width: int = 720
    fps: int = 15
    quality: int = 75
    cursor: float = 0.0


@dataclass
class EditorSession:
    user_id: int
    channel_id: int
    message_id: int
    input_path: str
    duration: float
    timeline: Timeline = field(default_factory=Timeline)
    history: list[dict] = field(default_factory=list)
    history_pos: int = -1
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_activity: float = field(default_factory=time.time)
    share_code: str = field(default_factory=_new_share_code)
    render_task: asyncio.Task | None = None
    cancel_flag: asyncio.Event = field(default_factory=asyncio.Event)
    # Not persisted. `channel`/`message` let us edit the editor message from
    # modal submits, where interaction.message points at the modal, not the editor.
    channel: Any | None = field(default=None, repr=False, compare=False)
    message: Any | None = field(default=None, repr=False, compare=False)


def tl_to_dict(tl: Timeline) -> dict:
    return asdict(tl)


def tl_from_dict(d: dict) -> Timeline:
    return Timeline(
        clips=[
            Clip(
                source=c["source"], start=c["start"], end=c["end"],
                speed=c.get("speed", 1.0),
                effects=[Effect(**e) for e in c.get("effects", [])],
            )
            for c in d.get("clips", [])
        ],
        overlays=[Overlay(**ov) for ov in d.get("overlays", [])],
        width=d.get("width", 720),
        fps=d.get("fps", 15),
        quality=d.get("quality", 75),
        cursor=d.get("cursor", 0.0),
    )


def render_signature(tl: Timeline) -> dict:
    # Cursor is UI-only and doesn't affect the render, so keep it out of the
    # cache key - otherwise every cursor move would invalidate the cache.
    d = tl_to_dict(tl)
    d.pop("cursor", None)
    return d


active_sessions: dict[int, EditorSession] = {}
