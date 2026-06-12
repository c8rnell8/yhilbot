import asyncio
import time
from collections import deque

import discord

from .logging_setup import log

queue_ids: deque[int] = deque()
queue_lock: asyncio.Lock = asyncio.Lock()

WAIT_TIMEOUT_SEC = 600
POLL_INTERVAL_SEC = 3


async def queue_wait(interaction: discord.Interaction) -> bool:
    """Enqueue an interaction and block until it reaches the front.

    Returns True once it's its turn (and removed from the queue), False if the
    interaction expired or the wait timed out.
    """
    async with queue_lock:
        queue_ids.append(interaction.id)
        pos = len(queue_ids)
    if pos > 1:
        try:
            await interaction.followup.send(f"📥 Вы в очереди. Позиция: `{pos}`")
        except Exception as e:
            log.warning(f"queue_wait: followup.send failed: {e}")

    wait_start = time.monotonic()
    while True:
        async with queue_lock:
            if queue_ids and queue_ids[0] == interaction.id:
                queue_ids.popleft()
                return True
            if interaction.id not in queue_ids:
                return False
            pos = list(queue_ids).index(interaction.id) + 1

        if time.monotonic() - wait_start > WAIT_TIMEOUT_SEC or interaction.is_expired():
            async with queue_lock:
                try:
                    queue_ids.remove(interaction.id)
                except ValueError:
                    pass
            if not interaction.is_expired():
                try:
                    await interaction.followup.send("⏳ Время ожидания истекло.")
                except Exception:
                    pass
            return False

        if pos > 1 and not interaction.is_expired():
            try:
                await interaction.edit_original_response(content=f"📥 Очередь. Позиция: `{pos}`")
            except Exception:
                pass
        await asyncio.sleep(POLL_INTERVAL_SEC)


async def queue_remove(interaction_id: int) -> None:
    async with queue_lock:
        try:
            queue_ids.remove(interaction_id)
        except ValueError:
            pass


def queue_length() -> int:
    return len(queue_ids)
