# yhilbot — web

Public site for [yhilbot](../README.md) — landing, live status, owner dashboard, and a placeholder for the in-browser editor port.

## Stack

- **Next.js 16** (App Router, RSC by default)
- **Tailwind v4** + **Geist Sans / Geist Mono**
- **next-intl 4** — three locales: `en`, `ua`, `ru`
- **Framer Motion** for spring-physics motion
- **Phosphor Icons** (no emojis anywhere — see [taste-skill](https://github.com/Leonxlnx/taste-skill))

## Routes

| Path                     | Purpose                                                                                                                                                                                                              |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/{locale}`              | Landing — hero with live status pill, command list (`/gif`, `/caption`, `/edit`, `/stats`, `/help`), engineering features.                                                                                           |
| `/{locale}/status`       | Live status board — uptime, queue depth, active sessions, CPU/RAM, lifetime counters. Polls `/api/status` every 5 s.                                                                                                  |
| `/{locale}/dashboard`    | Owner-only dashboard. UI is built; Discord OAuth is **not** wired in this commit. Disabled "Sign in with Discord" CTA + a preview of the metrics/history/limits panels populated from `/api/stats`.                  |
| `/{locale}/editor`       | Placeholder for the browser port of `/edit`. Reserves the route, layout, and keyboard shortcut surface.                                                                                                              |
| `/api/status`            | Mock JSON — proxies to `BOT_STATUS_URL` if set, otherwise returns a synthetic payload. Connect this to the bot's HTTP sidecar (e.g. `http://localhost:8080/status`) to make the page live.                           |
| `/api/stats`             | Same as above for `/dashboard`. Set `BOT_STATS_URL`.                                                                                                                                                                 |

## Local development

```bash
cd web
npm install
npm run dev   # http://localhost:3000 (auto-redirects to /en)
```

Lint + build (what CI runs):

```bash
npm run lint
npm run build
```

## Environment

| Variable          | Default | Purpose                                                                              |
| ----------------- | ------- | ------------------------------------------------------------------------------------ |
| `BOT_STATUS_URL`  | _none_  | Optional. URL of the bot's `/status` JSON endpoint. If unset the API returns mocks.  |
| `BOT_STATS_URL`   | _none_  | Optional. URL of the bot's `/stats` JSON endpoint.                                   |

No secrets are required to build or deploy.

## Deploying

The site is a vanilla Next.js project — drop it on Vercel, Netlify, or any Node host. For Vercel, point the project root to `web/`.

Recommended Vercel settings:

- Root directory: `web`
- Framework preset: Next.js (auto-detected)
- Install command: `npm install`
- Build command: `npm run build`
- Output: `.next` (default)

## Design system

This project follows [taste-skill](https://github.com/Leonxlnx/taste-skill):

- Geist Sans / Geist Mono only (no Inter)
- Single accent color (`emerald-500` at `--accent`)
- No emojis — Phosphor icons or pure typography
- `min-h-[100dvh]` instead of `h-screen`
- Grid over flex math
- Spring physics motion (no linear easing) on layout changes

## What's missing

- **Discord OAuth** for the dashboard — the UI is built; the auth wiring is the next PR.
- **Browser editor** — the page is a placeholder. The plan is to port the QUAD timeline UI to a Canvas/WebGL widget that posts render jobs to a small ffmpeg job queue running on the same machine as the bot.
- **HTTP sidecar on the bot** — the bot needs to expose `/status` and `/stats` endpoints (e.g. via `aiohttp.web` running alongside `discord.Client`). Until then, both API routes return mock data.
