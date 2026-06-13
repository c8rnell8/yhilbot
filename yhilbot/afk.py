"""Activity tracker → automatic AFK role.

Watches messages, reactions and voice. A member who does nothing for longer
than the configured window gets the AFK role; the moment they do anything the
role is taken off again. Everything is per-guild and persisted in the bot db,
so it survives restarts.

Needs the privileged **Server Members Intent** (enabled in client.py and in the
Discord Developer Portal → Bot). Without it the member scan can't run.
"""

import asyncio
import re
import time

import discord

from .client import client
from .editor.db import db_exec
from .logging_setup import log

# In-memory last-activity cache: (guild_id, user_id) -> unix ts. Write-through
# to the db is throttled so a busy chat doesn't hammer sqlite.
_last: dict[tuple[int, int], float] = {}
_dirty: dict[tuple[int, int], float] = {}
_PERSIST_EVERY = 120.0  # seconds
_SCAN_EVERY = 30 * 60   # seconds

# guild_id -> {"role_id": int, "threshold": int, "enabled": bool}
_config: dict[int, dict] = {}


async def init_afk() -> None:
    await db_exec(
        """
        CREATE TABLE IF NOT EXISTS afk_config (
            guild_id  INTEGER PRIMARY KEY,
            role_id   INTEGER,
            threshold INTEGER,
            enabled   INTEGER
        )
        """
    )
    await db_exec(
        """
        CREATE TABLE IF NOT EXISTS afk_activity (
            guild_id    INTEGER,
            user_id     INTEGER,
            last_active REAL,
            PRIMARY KEY (guild_id, user_id)
        )
        """
    )
    # Warm the caches from disk.
    for gid, role_id, threshold, enabled in await db_exec(
        "SELECT guild_id, role_id, threshold, enabled FROM afk_config", fetch=True
    ) or []:
        _config[gid] = {"role_id": role_id, "threshold": threshold, "enabled": bool(enabled)}
    for gid, uid, ts in await db_exec(
        "SELECT guild_id, user_id, last_active FROM afk_activity", fetch=True
    ) or []:
        _last[(gid, uid)] = ts


def get_config(guild_id: int) -> dict | None:
    return _config.get(guild_id)


async def set_config(guild_id: int, role_id: int, threshold: int, enabled: bool) -> None:
    _config[guild_id] = {"role_id": role_id, "threshold": threshold, "enabled": enabled}
    await db_exec(
        "INSERT OR REPLACE INTO afk_config VALUES (?,?,?,?)",
        (guild_id, role_id, threshold, 1 if enabled else 0),
    )


async def _persist(key: tuple[int, int], ts: float) -> None:
    await db_exec(
        "INSERT OR REPLACE INTO afk_activity VALUES (?,?,?)", (key[0], key[1], ts)
    )


async def _touch(guild_id: int, member: discord.Member | None, user_id: int) -> None:
    """Record activity and clear the AFK role if the member had it."""
    if guild_id is None:
        return
    now = time.time()
    key = (guild_id, user_id)
    prev = _last.get(key, 0)
    _last[key] = now
    # throttle db writes
    if now - _dirty.get(key, 0) > _PERSIST_EVERY:
        _dirty[key] = now
        await _persist(key, now)

    cfg = _config.get(guild_id)
    if not cfg or not cfg["enabled"]:
        return
    # Only bother fetching/removing the role if they were idle long enough to
    # plausibly have it.
    if prev and now - prev < cfg["threshold"]:
        return
    role = _afk_role(guild_id)
    if not role:
        return
    try:
        m = member or await _resolve_member(guild_id, user_id)
        if m and role in m.roles and not m.bot:
            await m.remove_roles(role, reason="Знову активний")
            log.info(f"afk: removed role from {m} in guild {guild_id}")
    except Exception as e:  # noqa: BLE001
        log.warning(f"afk: remove role failed: {e}")


def _afk_role(guild_id: int) -> discord.Role | None:
    cfg = _config.get(guild_id)
    if not cfg:
        return None
    guild = client.get_guild(guild_id)
    return guild.get_role(cfg["role_id"]) if guild else None


async def _resolve_member(guild_id: int, user_id: int) -> discord.Member | None:
    guild = client.get_guild(guild_id)
    if not guild:
        return None
    m = guild.get_member(user_id)
    if m:
        return m
    try:
        return await guild.fetch_member(user_id)
    except Exception:  # noqa: BLE001
        return None


def inactivity_seconds(guild_id: int, user_id: int) -> float:
    ts = _last.get((guild_id, user_id))
    return time.time() - ts if ts else 0.0


def format_duration(sec: float) -> str:
    """'13 д' up to a month, then '1 м, 13 д'. Sub-day shows hours/minutes."""
    if sec < 3600:
        return f"{int(sec // 60)} хв"
    if sec < 86400:
        return f"{int(sec // 3600)} год"
    days = int(sec // 86400)
    if days <= 30:
        return f"{days} д"
    months = days // 30
    rem = days % 30
    return f"{months} м, {rem} д"


_UNIT_SEC = {"mo": 2592000, "w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int | None:
    """Turn '30d', '2w', '3months', '12h', '45m', '90s' (and combos like
    '1w2d') into seconds. A bare number means days. Returns None if unparsable.
    Note: m = minutes, months/mo = months."""
    t = text.strip().lower().replace(" ", "")
    if not t:
        return None
    if t.isdigit():
        return int(t) * 86400
    t = t.replace("months", "mo").replace("month", "mo").replace("mon", "mo")
    # 'mo' must be tried before 'm' so months aren't read as minutes.
    matches = re.findall(r"(\d+)(mo|w|d|h|m|s)", t)
    if not matches:
        return None
    # reject leftover junk (e.g. "30x")
    if "".join(n + u for n, u in matches) != t:
        return None
    return sum(int(n) * _UNIT_SEC[u] for n, u in matches)


# ---- events ---------------------------------------------------------------

@client.event
async def on_message(message: discord.Message) -> None:
    if message.guild and not message.author.bot:
        await _touch(message.guild.id, message.author, message.author.id)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    if payload.guild_id and payload.user_id and payload.user_id != client.user.id:
        await _touch(payload.guild_id, payload.member, payload.user_id)


@client.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    if member.guild and not member.bot:
        # any voice change (join/leave/mute/move) counts as activity
        await _touch(member.guild.id, member, member.id)


# ---- background scan ------------------------------------------------------

async def _scan_once() -> None:
    now = time.time()
    for guild_id, cfg in list(_config.items()):
        if not cfg["enabled"]:
            continue
        guild = client.get_guild(guild_id)
        if not guild:
            continue
        role = guild.get_role(cfg["role_id"])
        if not role:
            continue
        threshold = cfg["threshold"]
        for member in guild.members:
            if member.bot:
                continue
            key = (guild_id, member.id)
            ts = _last.get(key)
            if ts is None:
                # First time we see them — start their clock now so nobody is
                # marked AFK just because the bot only just started tracking.
                _last[key] = now
                await _persist(key, now)
                continue
            idle = now - ts
            has_role = role in member.roles
            try:
                if idle > threshold and not has_role:
                    await member.add_roles(role, reason="Неактивний")
                    log.info(f"afk: marked {member} AFK in guild {guild_id}")
                elif idle <= threshold and has_role:
                    await member.remove_roles(role, reason="Знову активний")
            except discord.Forbidden:
                log.warning(f"afk: no permission to manage roles in guild {guild_id}")
                break
            except Exception as e:  # noqa: BLE001
                log.warning(f"afk: scan role op failed: {e}")


async def _scan_loop() -> None:
    await asyncio.sleep(60)  # let the gateway finish chunking members
    while True:
        try:
            await _scan_once()
        except Exception as e:  # noqa: BLE001
            log.warning(f"afk: scan loop error: {e}")
        await asyncio.sleep(_SCAN_EVERY)


_started = False


def start() -> None:
    global _started
    if _started:
        return
    _started = True
    client.loop.create_task(_scan_loop())
