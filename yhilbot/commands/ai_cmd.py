import json
import logging
import time

import aiohttp
import discord

from .. import config
from ..client import tree

log = logging.getLogger("yhilbot.ai")

# The -latest alias follows whatever lite model Google serves free right now;
# the rest are fallbacks for quota/overload hiccups. Same list as the site.
_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

_SYSTEM = (
    "Ти — бот клану «Ухилянти» (Squad / Arma Reforger) в Discord. "
    "Відповідай коротко і по суті, тією мовою, якою питають (українська або російська). "
    "Можеш жартувати у військовому стилі спільноти, але без образ. "
    "Якщо питають про команди бота: /gif, /caption, /edit, /webedit, /stats, /help, /ai."
)

_MAX_PROMPT = 2000
_COOLDOWN_SEC = 10
_last_use: dict[int, float] = {}


async def _ask(prompt: str) -> str:
    key = config.GEMINI_API_KEY
    if not key:
        return "AI не налаштований: немає GEMINI_API_KEY у yhil.env."

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }

    last_err = "Gemini недоступний."
    async with aiohttp.ClientSession() as http:
        for model in _MODELS:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            try:
                async with http.post(
                    url,
                    json=body,
                    headers={"x-goog-api-key": key},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as res:
                    if res.status in (404, 429, 503):
                        last_err = f"Gemini {res.status}, пробую іншу модель..."
                        continue
                    data = json.loads(await res.text())
                    if res.status != 200:
                        msg = data.get("error", {}).get("message", "")
                        return f"Gemini повернув {res.status}: {msg[:200]}"
                    parts = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [])
                    )
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if text:
                        return text
                    last_err = "Порожня відповідь від Gemini."
            except Exception as e:  # noqa: BLE001 - report any network failure to chat
                last_err = f"Не достукався до Gemini: {e}"
    return last_err


@tree.command(name="ai", description="Спитати штучний інтелект (Gemini)")
@discord.app_commands.describe(prompt="Питання або прохання")
async def ai_cmd(interaction: discord.Interaction, prompt: str) -> None:
    now = time.time()
    prev = _last_use.get(interaction.user.id, 0)
    if now - prev < _COOLDOWN_SEC and interaction.user.id != config.OWNER_ID:
        await interaction.response.send_message(
            f"Зачекай {int(_COOLDOWN_SEC - (now - prev)) + 1} с перед наступним питанням.",
            ephemeral=True,
        )
        return
    _last_use[interaction.user.id] = now

    prompt = prompt.strip()[:_MAX_PROMPT]
    if not prompt:
        await interaction.response.send_message("Питання порожнє.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    answer = await _ask(prompt)

    # Discord caps a message at 2000 chars - split long answers.
    chunks = [answer[i : i + 1990] for i in range(0, len(answer), 1990)] or ["..."]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:3]:
        await interaction.followup.send(chunk)
