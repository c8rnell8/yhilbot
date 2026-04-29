"use client";

import {
  ChartBarIcon,
  CpuIcon,
  FilmReelIcon,
  HardDrivesIcon,
  StackIcon,
  TimerIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

type StatusPayload = {
  online: boolean;
  uptime_seconds: number;
  queue_depth: number;
  active_sessions: number;
  renders_today: number;
  cpu_percent: number;
  memory_percent: number;
  counters: {
    gif_ok: number;
    caption_ok: number;
    edit_ok: number;
  };
  last_update: string;
  mock?: boolean;
};

function formatUptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function StatusBoard() {
  const t = useTranslations("Status");
  const fmt = useFormatter();
  const [data, setData] = useState<StatusPayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await fetch("/api/status", { cache: "no-store" });
        if (!r.ok) return;
        const json: StatusPayload = await r.json();
        if (!cancelled) setData(json);
      } catch {
        /* ignore */
      }
    }
    load();
    const id = setInterval(load, 5_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const metrics: ReadonlyArray<{
    key: keyof StatusPayload | "uptime" | "memory" | "cpu";
    label: string;
    value: string;
    Icon: Icon;
    accent?: boolean;
  }> = [
    {
      key: "uptime",
      label: t("metrics.uptime"),
      value: data ? formatUptime(data.uptime_seconds) : "—",
      Icon: TimerIcon,
      accent: true,
    },
    {
      key: "queue_depth",
      label: t("metrics.queue"),
      value: data ? String(data.queue_depth) : "—",
      Icon: StackIcon,
    },
    {
      key: "active_sessions",
      label: t("metrics.sessions"),
      value: data ? String(data.active_sessions) : "—",
      Icon: ChartBarIcon,
    },
    {
      key: "renders_today",
      label: t("metrics.renders"),
      value: data ? fmt.number(data.renders_today) : "—",
      Icon: FilmReelIcon,
    },
    {
      key: "cpu",
      label: t("metrics.cpu"),
      value: data ? `${data.cpu_percent.toFixed(1)}%` : "—",
      Icon: CpuIcon,
    },
    {
      key: "memory",
      label: t("metrics.memory"),
      value: data ? `${data.memory_percent.toFixed(1)}%` : "—",
      Icon: HardDrivesIcon,
    },
  ];

  return (
    <div className="space-y-12">
      <div className="grid divide-y divide-[color:var(--border)] sm:divide-y-0 sm:grid-cols-2 lg:grid-cols-3 sm:divide-x">
        {metrics.map(({ key, label, value, Icon, accent }, idx) => (
          <motion.div
            key={key as string}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: idx * 0.04, ease: [0.16, 1, 0.3, 1] }}
            className="px-6 py-7 first:pl-0 last:pr-0 flex items-start justify-between gap-3"
          >
            <div>
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono">
                {label}
              </div>
              <div
                className={`mt-2 text-3xl md:text-4xl tracking-tighter font-medium ${
                  accent ? "text-[color:var(--accent)]" : ""
                }`}
              >
                {value}
              </div>
            </div>
            <Icon className="size-5 text-[color:var(--muted)]" weight="regular" aria-hidden />
          </motion.div>
        ))}
      </div>

      <section aria-labelledby="counters-title" className="border-t border-[color:var(--border)] pt-10">
        <h2
          id="counters-title"
          className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono"
        >
          {t("counters.title")}
        </h2>
        <dl className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-x-10 gap-y-6">
          <CounterRow label={t("counters.gifOk")} value={data?.counters.gif_ok ?? null} fmt={fmt} />
          <CounterRow
            label={t("counters.captionOk")}
            value={data?.counters.caption_ok ?? null}
            fmt={fmt}
          />
          <CounterRow label={t("counters.editOk")} value={data?.counters.edit_ok ?? null} fmt={fmt} />
        </dl>
      </section>

      <div className="flex flex-col gap-2 text-xs text-[color:var(--muted)] font-mono">
        <span>
          {t("lastUpdate", {
            when: data ? new Date(data.last_update).toLocaleString() : "—",
          })}
        </span>
        {data?.mock && (
          <span className="inline-flex items-center gap-1.5">
            <WarningCircleIcon className="size-3.5" weight="fill" aria-hidden />
            {t("demoNotice")}
          </span>
        )}
      </div>
    </div>
  );
}

function CounterRow({
  label,
  value,
  fmt,
}: {
  label: string;
  value: number | null;
  fmt: ReturnType<typeof useFormatter>;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono">
        {label}
      </dt>
      <dd className="mt-1 text-2xl tracking-tight font-medium font-mono">
        {value === null ? "—" : fmt.number(value)}
      </dd>
    </div>
  );
}
