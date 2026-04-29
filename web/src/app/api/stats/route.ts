import { NextResponse } from "next/server";

export const runtime = "edge";
export const dynamic = "force-dynamic";

type RecentRender = {
  id: string;
  user: string;
  duration_seconds: number;
  size_bytes: number;
  status: "ok" | "fail" | "cancel";
  finished_at: string;
};

const MOCK_RECENT: ReadonlyArray<RecentRender> = [
  {
    id: "r_8XK9",
    user: "@hueta",
    duration_seconds: 8.4,
    size_bytes: 6_321_000,
    status: "ok",
    finished_at: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
  },
  {
    id: "r_8XK8",
    user: "@vasya",
    duration_seconds: 12.0,
    size_bytes: 9_812_000,
    status: "ok",
    finished_at: new Date(Date.now() - 1000 * 60 * 11).toISOString(),
  },
  {
    id: "r_8XK7",
    user: "@petya",
    duration_seconds: 22.6,
    size_bytes: 24_998_000,
    status: "fail",
    finished_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
  },
  {
    id: "r_8XK6",
    user: "@hueta",
    duration_seconds: 4.0,
    size_bytes: 2_104_000,
    status: "ok",
    finished_at: new Date(Date.now() - 1000 * 60 * 64).toISOString(),
  },
  {
    id: "r_8XK5",
    user: "@kola",
    duration_seconds: 16.2,
    size_bytes: 13_440_000,
    status: "cancel",
    finished_at: new Date(Date.now() - 1000 * 60 * 121).toISOString(),
  },
];

export async function GET() {
  const upstream = process.env.BOT_STATS_URL;

  if (upstream) {
    try {
      const r = await fetch(upstream, { cache: "no-store" });
      if (r.ok) {
        const data = await r.json();
        return NextResponse.json(data, { headers: { "cache-control": "no-store" } });
      }
    } catch {
      // fall through
    }
  }

  return NextResponse.json(
    {
      today: {
        renders: 14,
        uptime_seconds: 3600 * 17 + 41 * 60,
        errors: 1,
        queue_depth: 0,
      },
      limits: {
        concurrent_renders: 1,
        concurrent_converts: 4,
        max_input_mb: 100,
        output_limit_mb: 25,
      },
      recent: MOCK_RECENT,
      mock: true,
    },
    { headers: { "cache-control": "no-store" } }
  );
}
