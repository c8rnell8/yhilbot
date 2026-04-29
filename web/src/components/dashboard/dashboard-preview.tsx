"use client";

import {
  CheckCircleIcon,
  ClockCounterClockwiseIcon,
  ProhibitIcon,
  WarningOctagonIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

type Recent = {
  id: string;
  user: string;
  duration_seconds: number;
  size_bytes: number;
  status: "ok" | "fail" | "cancel";
  finished_at: string;
};

type StatsPayload = {
  today: {
    renders: number;
    uptime_seconds: number;
    errors: number;
    queue_depth: number;
  };
  limits: {
    concurrent_renders: number;
    concurrent_converts: number;
    max_input_mb: number;
    output_limit_mb: number;
  };
  recent: ReadonlyArray<Recent>;
};

const STATUS_ICONS: Record<Recent["status"], { Icon: Icon; tone: string }> = {
  ok: { Icon: CheckCircleIcon, tone: "text-[color:var(--accent)]" },
  fail: { Icon: WarningOctagonIcon, tone: "text-rose-500" },
  cancel: { Icon: ProhibitIcon, tone: "text-amber-500" },
};

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function formatUptime(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function DashboardPreview() {
  const t = useTranslations("Dashboard");
  const fmt = useFormatter();
  const [data, setData] = useState<StatsPayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/stats", { cache: "no-store" })
      .then((r) => r.json())
      .then((d: StatsPayload) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-14">
      {/* metrics */}
      <section aria-labelledby="dash-metrics">
        <h2
          id="dash-metrics"
          className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono mb-5"
        >
          {t("metrics.title")}
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-[color:var(--border)] border-y border-[color:var(--border)]">
          <Metric label={t("metrics.renders")} value={data ? fmt.number(data.today.renders) : "—"} accent />
          <Metric label={t("metrics.uptime")} value={data ? formatUptime(data.today.uptime_seconds) : "—"} />
          <Metric label={t("metrics.errors")} value={data ? fmt.number(data.today.errors) : "—"} />
          <Metric label={t("metrics.queue")} value={data ? fmt.number(data.today.queue_depth) : "—"} />
        </div>
      </section>

      {/* recent renders */}
      <section aria-labelledby="dash-history">
        <h2
          id="dash-history"
          className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono mb-5"
        >
          {t("history.title")}
        </h2>
        <div className="overflow-x-auto rounded-2xl border border-[color:var(--border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[color:var(--muted)] font-mono uppercase text-[11px] tracking-wide">
                <th className="px-5 py-3 font-normal">{t("history.user")}</th>
                <th className="px-5 py-3 font-normal">{t("history.duration")}</th>
                <th className="px-5 py-3 font-normal">{t("history.size")}</th>
                <th className="px-5 py-3 font-normal">{t("history.status")}</th>
                <th className="px-5 py-3 font-normal">{t("history.when")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--border)]">
              {data?.recent.map((row, idx) => {
                const { Icon, tone } = STATUS_ICONS[row.status];
                return (
                  <motion.tr
                    key={row.id}
                    initial={{ opacity: 0, y: 6 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.35, delay: idx * 0.03, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <td className="px-5 py-4 font-mono">{row.user}</td>
                    <td className="px-5 py-4 font-mono">{row.duration_seconds.toFixed(1)}s</td>
                    <td className="px-5 py-4 font-mono">{formatBytes(row.size_bytes)}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-1.5 ${tone}`}>
                        <Icon className="size-4" weight="fill" aria-hidden />
                        <span className="text-sm">{t(`history.${row.status}`)}</span>
                      </span>
                    </td>
                    <td className="px-5 py-4 text-[color:var(--muted)]">
                      {new Date(row.finished_at).toLocaleString()}
                    </td>
                  </motion.tr>
                );
              })}
              {!data && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-[color:var(--muted)]">
                    <ClockCounterClockwiseIcon className="size-5 mx-auto mb-2" aria-hidden />
                    Loading…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* limits */}
      <section aria-labelledby="dash-limits">
        <h2
          id="dash-limits"
          className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono mb-5"
        >
          {t("limits.title")}
        </h2>
        <form
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 border-t border-[color:var(--border)] pt-6"
          onSubmit={(e) => e.preventDefault()}
        >
          <LimitField label={t("limits.concurrentRenders")} value={data?.limits.concurrent_renders} />
          <LimitField label={t("limits.concurrentConverts")} value={data?.limits.concurrent_converts} />
          <LimitField label={t("limits.maxInputMb")} value={data?.limits.max_input_mb} />
          <LimitField label={t("limits.outputLimitMb")} value={data?.limits.output_limit_mb} />
          <div className="md:col-span-2 lg:col-span-4 flex">
            <button
              type="submit"
              disabled
              className="inline-flex items-center gap-2 h-10 px-5 rounded-full bg-[color:var(--foreground)]/10 text-[color:var(--muted)] text-sm font-medium cursor-not-allowed"
            >
              {t("limits.save")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="px-6 py-7 first:pl-0 last:pr-0">
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
  );
}

function LimitField({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono">
        {label}
      </label>
      <input
        type="number"
        defaultValue={value ?? ""}
        disabled
        className="h-10 px-3 rounded-lg border border-[color:var(--border)] bg-transparent text-sm font-mono disabled:opacity-60 disabled:cursor-not-allowed"
      />
    </div>
  );
}
