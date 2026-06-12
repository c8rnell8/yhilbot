# yhilbot

A Discord bot for media editing: GIF/WebP conversion, meme captions over images,
and a QUAD video editor with an ffmpeg-based timeline.

## Commands

| Command | What it does |
|---|---|
| `/gif [media]` | Converts video to an animated WebP, or an image to a GIF. Picks resolution and FPS automatically to stay under Discord's ~25 MB limit. |
| `/caption <text> [media]` | Draws a meme caption in Impact over an image. |
| `/edit [media] [join_code]` | Timeline video editor: split, text overlays, speed, resolution, FPS, undo/redo, background render. |
| `/stats` | Bot, resource and queue stats (owner only). |
| `/help` | Command list. |

`media` is optional - if you leave it out, the bot grabs the first media file
from the last 15 messages in the channel.

## Setup

```bash
git clone https://github.com/c8rnell8/yhilbot.git
cd yhilbot

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp yhil.env.example yhil.env
# edit yhil.env and set DISCORD_TOKEN and OWNER_ID

python bot.py
```

## Requirements

- Python 3.10+
- ffmpeg + ffprobe on `$PATH` (with libwebp, libgif, drawtext)
- Impact font (or a Liberation/DejaVu fallback) for `/caption`
- Optional: `h264_nvenc` for GPU-accelerated rendering
- Optional: `psutil` for extended stats

## Layout

```
bot.py                           # entry point
yhilbot/
├── config.py                    # env config and paths
├── logging_setup.py             # logger
├── stats.py                     # counters
├── client.py                    # Discord client and command tree
├── ffmpeg_helpers.py            # ffmpeg/ffprobe wrappers + escaping
├── media_utils.py               # downloading and finding channel media
├── caption_render.py            # PIL rendering for /caption
├── queue_mgr.py                 # global /gif queue
├── cache.py                     # render_cache/gif_cache helpers
├── lifecycle.py                 # on_ready, graceful shutdown
├── editor/
│   ├── models.py                # Clip/Overlay/Timeline/EditorSession
│   ├── db.py                    # sqlite + thread-local connection
│   ├── history.py               # undo/redo
│   ├── preview.py               # preview frame generation
│   ├── render.py                # background render with progress
│   ├── modals.py                # TimeModal, TextOverlayModal
│   ├── view.py                  # EditorView (buttons and selects)
│   └── cleanup.py               # background cleanup of stale sessions/cache
└── commands/
    ├── gif_cmd.py
    ├── caption_cmd.py
    ├── edit_cmd.py
    ├── stats_cmd.py
    └── help_cmd.py
```

## Default limits

- Input: up to 100 MB (`MAX_INPUT_MB`)
- Video: up to 5 minutes
- Output: <= 24.5 MB (Discord without boost)
- Edit history: 25 steps
- Editor timeout: 15 minutes idle
- Cache TTL: 2 hours

## Development

```bash
pip install ruff
ruff check yhilbot bot.py
```
