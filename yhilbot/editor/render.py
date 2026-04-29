"""Фоновый рендер таймлайна с прогрессом и адаптивным даунскейлом."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import time

import discord
import psutil

from .. import config
from ..cache import cache_key, cache_path
from ..ffmpeg_helpers import (
    escape_textfile_path,
    sanitize_color,
    write_overlay_text_file,
)
from ..logging_setup import log
from ..stats import stats
from .models import EditorSession, render_signature, tl_from_dict, tl_to_dict

# Семафор параллельных рендеров. Без него параллельные нажатия «Рендер»
# в нескольких сессиях клали CPU/диск.
_render_semaphore: asyncio.Semaphore | None = None


def _get_render_semaphore() -> asyncio.Semaphore:
    global _render_semaphore
    if _render_semaphore is None:
        _render_semaphore = asyncio.Semaphore(config.CONCURRENT_RENDERS)
    return _render_semaphore


async def check_resources() -> tuple[bool, str]:
    """Быстрая проверка CPU/RAM/disk перед запуском рендера.

    `cpu_percent(interval=None)` — мгновенный (использует delta с прошлого вызова),
    в отличие от `interval=0.1` который блокировал event loop на 100мс.
    """
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(config.TEMP_DIR)
    except Exception:
        return True, ""
    if cpu > 85:
        return False, f"🔥 CPU перегружен ({cpu:.0f}%)."
    if mem > 90:
        return False, f"🧠 RAM перегружена ({mem:.0f}%)."
    if disk.free < 1024 ** 3:
        return False, "💾 Мало места на диске (<1 ГБ)."
    return True, ""


def _build_cmd(
    tl_dict: dict,
    out_path: str,
    sc: int, fr: int, ql: int,
    overlay_files: list[str],
) -> list[str]:
    """Строит ffmpeg-команду по сериализованному таймлайну.

    `tl_dict` — снапшот, чтобы UI-мутации во время рендера не ломали filtergraph.
    `overlay_files` — заранее записанные текстовые файлы для drawtext=textfile=.
    """
    inputs: list[str] = []
    filters: list[str] = []
    clips = tl_dict.get("clips", [])
    overlays = tl_dict.get("overlays", [])

    for c in clips:
        inputs += ["-i", c["source"]]

    for i, c in enumerate(clips):
        chain = [
            f"trim=start={c['start']}:end={c['end']}",
            "setpts=PTS-STARTPTS",
        ]
        speed = c.get("speed", 1.0)
        if speed != 1.0:
            chain.append(f"setpts={1 / max(0.1, speed)}*PTS")
        for eff in c.get("effects", []):
            name = eff.get("name", "")
            if name == "zoom":
                chain.append("zoompan=z='min(zoom+0.002,1.2)'")
            elif name == "blur":
                chain.append("boxblur=2")
        chain += [f"scale={sc}:-1:flags=lanczos", f"fps={fr}", "format=rgba"]
        filters.append(f"[{i}:v]{','.join(chain)}[v{i}]")

    concat_in = "".join(f"[v{i}]" for i in range(len(clips)))
    filters.append(f"{concat_in}concat=n={len(clips)}:v=1:a=0[base]")

    last = "[base]"
    for idx, ov in enumerate(overlays):
        text_path = escape_textfile_path(overlay_files[idx])
        color = sanitize_color(ov.get("color"))
        size = int(ov.get("size", 40))
        x = ov.get("x", "(w-text_w)/2")
        y = ov.get("y", "50")
        # x/y — это ffmpeg-выражения; их пользователь напрямую не задаёт через UI,
        # значения приходят из дефолтов Overlay. Если когда-нибудь добавишь поле
        # ввода координат — обязательно добавь sanitize.
        enab = f"between(t\\,{ov['start']}\\,{ov['end']})"
        filters.append(
            f"{last}drawtext=textfile='{text_path}':x={x}:y={y}:"
            f"fontsize={size}:fontcolor={color}:enable='{enab}'[ov{idx}]"
        )
        last = f"[ov{idx}]"

    return (
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", ";".join(filters),
            "-map", last,
            "-c:v", "libwebp", "-lossless", "0",
            "-quality", str(ql), "-compression_level", "6",
            "-loop", "0", "-preset", "default",
            "-an", "-progress", "pipe:1", "-nostats", out_path,
        ]
    )


async def _drain_stderr(proc: asyncio.subprocess.Process) -> bytes:
    """Дренирует stderr-pipe, чтобы ffmpeg не залип на write() при больших ошибках."""
    if proc.stderr is None:
        return b""
    try:
        return await proc.stderr.read()
    except Exception:
        return b""


async def background_render(sess: EditorSession, interaction: discord.Interaction) -> None:
    """Главная корутина рендера (запускается через asyncio.create_task)."""
    mid = sess.message_id
    out = os.path.join(config.TEMP_DIR, f"render_{mid}.webp")
    target = int(config.OUTPUT_LIMIT_MB * 1024 * 1024)
    channel = interaction.channel
    user = interaction.user

    # Снапшот таймлайна — чтобы Undo/Redo во время рендера не ломали build_cmd.
    async with sess.lock:
        tl_dict = tl_to_dict(sess.timeline)
    tl_for_calc = tl_from_dict(tl_dict)

    # Кэш по сигнатуре без cursor
    ck = cache_key(render_signature(tl_for_calc))
    cached_out = cache_path(ck, ext="webp")
    if os.path.exists(cached_out):
        try:
            file = discord.File(cached_out, filename="result.webp")
            msg = "✅ Готово (из кэша)!"
            sent = False
            try:
                if not interaction.is_expired():
                    await interaction.followup.send(msg, file=file)
                    sent = True
                else:
                    await channel.send(f"{user.mention} {msg}", file=file)
                    sent = True
            except Exception as e:
                log.warning(f"render: cache-hit send failed: {e}")
            if sent:
                stats.inc("edit_ok")
        except Exception as e:
            log.warning(f"render: cache-hit failed: {e}")
        return

    # Готовим overlay-файлы (один раз на рендер; чистим в finally)
    overlay_files: list[str] = []
    for idx, ov in enumerate(tl_dict.get("overlays", [])):
        try:
            overlay_files.append(write_overlay_text_file(ov["text"], mid, idx))
        except Exception as e:
            log.warning(f"render: write overlay text {idx}: {e}")
            overlay_files.append("")

    ticket: discord.Message | None = None
    try:
        ticket = await channel.send(f"🎫 Рендер `#{mid}` запущен...")
    except Exception:
        pass

    sess.cancel_flag.clear()
    last_prog = 0.0
    ok = False
    scale = tl_for_calc.width
    fps = tl_for_calc.fps
    qual = tl_for_calc.quality
    attempts = 0

    total_dur = (
        sum(max(0.01, (c.end - c.start) / max(0.1, c.speed)) for c in tl_for_calc.clips)
        if tl_for_calc.clips else 1.0
    )

    async def update_progress(pct: float, eta: float) -> None:
        nonlocal last_prog
        now = time.time()
        if now - last_prog < 2.5 and pct < 1.0:
            return
        last_prog = now
        bar = "█" * int(pct * 12) + "░" * (12 - int(pct * 12))
        eta_str = f"⏳ {int(eta // 60)}м {int(eta % 60)}с" if eta > 0 else "✅ Готово"
        txt = f"🎬 Рендер `#{mid}` | {bar} {int(pct * 100)}% | {eta_str}"
        try:
            if ticket:
                await ticket.edit(content=txt)
        except Exception:
            pass

    async def parse_progress(proc: asyncio.subprocess.Process) -> None:
        total_us = total_dur * 1_000_000
        if proc.stdout is None:
            return
        while True:
            if sess.cancel_flag.is_set():
                try:
                    proc.kill()
                except Exception:
                    pass
                return
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode(errors="ignore")
            m_t = re.search(r"out_time_ms=(\d+)", decoded)
            m_s = re.search(r"speed=([\d.]+)x", decoded)
            if m_t and m_s:
                out_us = int(m_t.group(1))
                ffspeed = max(0.01, float(m_s.group(1)))
                pct = min(1.0, out_us / total_us) if total_us > 0 else 0.0
                remaining = max(0.0, (total_us - out_us) / (ffspeed * 1_000_000))
                await update_progress(pct, remaining)

    sem = _get_render_semaphore()
    try:
        async with sem:
            while attempts <= 5:
                if sess.cancel_flag.is_set():
                    break
                # Регенерим overlay-файлы если их потёрли (idempotent)
                for idx, ov in enumerate(tl_dict.get("overlays", [])):
                    if not overlay_files[idx] or not os.path.exists(overlay_files[idx]):
                        try:
                            overlay_files[idx] = write_overlay_text_file(ov["text"], mid, idx)
                        except Exception:
                            pass

                cmd = _build_cmd(tl_dict, out, scale, fps, qual, overlay_files)
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                try:
                    # Параллельно: парсим прогресс из stdout, дренируем stderr.
                    stderr_task = asyncio.create_task(_drain_stderr(proc))
                    await parse_progress(proc)
                    await proc.wait()
                    err_bytes = await stderr_task
                    if proc.returncode == 0 and os.path.exists(out):
                        fsize = os.path.getsize(out)
                        if fsize <= target:
                            ok = True
                            break
                        ratio = (target / max(1, fsize)) ** 0.5
                        scale = max(320, int(scale * ratio))
                        fps = max(6, int(fps * ratio))
                        qual = max(20, int(qual * ratio))
                    else:
                        log.warning(
                            f"render attempt {attempts}: rc={proc.returncode} "
                            f"err={err_bytes.decode(errors='replace')[-300:]}"
                        )
                except Exception as e:
                    log.warning(f"render attempt {attempts}: {e}")
                attempts += 1

        if ok and os.path.exists(out):
            try:
                shutil.copy2(out, cached_out)
            except Exception:
                pass

        if sess.cancel_flag.is_set():
            txt = f"🛑 Рендер `#{mid}` отменён."
            try:
                if not interaction.is_expired():
                    await interaction.followup.send(txt)
                else:
                    await channel.send(f"{user.mention} {txt}")
            except Exception as e:
                log.warning(f"render: cancel notice failed: {e}")
        elif ok and os.path.exists(out):
            sz = os.path.getsize(out) / 1024 / 1024
            txt = f"✅ Рендер `#{mid}` готов! `{sz:.2f} МБ`"
            sent = False
            try:
                file = discord.File(out, filename="result.webp")
                if not interaction.is_expired():
                    await interaction.followup.send(content=txt, file=file)
                    sent = True
                else:
                    await channel.send(content=f"{user.mention} {txt}", file=file)
                    sent = True
            except Exception as e:
                log.warning(f"render: send failed: {e}")
                try:
                    await user.send(content=txt, file=discord.File(out, filename="result.webp"))
                    sent = True
                except Exception:
                    pass
            if sent:
                stats.inc("edit_ok")
            else:
                stats.inc("edit_fail")
        else:
            stats.inc("edit_fail")
            txt = f"❌ Рендер `#{mid}` не удалось уложить в {config.OUTPUT_LIMIT_MB} МБ."
            try:
                if not interaction.is_expired():
                    await interaction.followup.send(txt)
                else:
                    await channel.send(f"{user.mention} {txt}")
            except Exception as e:
                log.warning(f"render: failure notice failed: {e}")
    finally:
        if ticket:
            try:
                await ticket.delete()
            except Exception:
                pass
        if os.path.exists(out):
            try:
                os.remove(out)
            except Exception:
                pass
        for tf in overlay_files:
            if tf and os.path.exists(tf):
                try:
                    os.remove(tf)
                except Exception:
                    pass
