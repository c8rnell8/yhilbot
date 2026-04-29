import { NextResponse } from "next/server";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export async function GET() {
  // Replace this with a fetch to the bot's HTTP sidecar (e.g. http://bot:8080/status)
  // and propagate the JSON it returns. For now we synthesize plausible data.
  const upstream = process.env.BOT_STATUS_URL;

  if (upstream) {
    try {
      const r = await fetch(upstream, { cache: "no-store" });
      if (r.ok) {
        const data = await r.json();
        return NextResponse.json(data, { headers: { "cache-control": "no-store" } });
      }
    } catch {
      // fall through to mock
    }
  }

  return NextResponse.json(
    {
      online: true,
      uptime_seconds: 3600 * 17 + 41 * 60,
      queue_depth: 0,
      active_sessions: 2,
      renders_today: 14,
      cpu_percent: 8.4,
      memory_percent: 31.2,
      counters: {
        gif_ok: 1284,
        caption_ok: 412,
        edit_ok: 207,
      },
      last_update: new Date().toISOString(),
      mock: true,
    },
    { headers: { "cache-control": "no-store" } }
  );
}
