"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

type Status = "online" | "offline" | "checking";

export function StatusPill() {
  const t = useTranslations("Hero");
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      try {
        const r = await fetch("/api/status", { cache: "no-store" });
        const data: { online: boolean } = await r.json();
        if (!cancelled) setStatus(data.online ? "online" : "offline");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    tick();
    const id = setInterval(tick, 15_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const label =
    status === "online"
      ? t("statusOnline")
      : status === "offline"
        ? t("statusOffline")
        : t("statusChecking");

  const dotColor =
    status === "online"
      ? "bg-[color:var(--accent)]"
      : status === "offline"
        ? "bg-rose-500"
        : "bg-amber-500";

  return (
    <span
      className="inline-flex items-center gap-2 px-3 h-7 rounded-full border border-[color:var(--border)] text-xs font-mono tracking-tight"
      role="status"
      aria-live="polite"
    >
      <span className="relative flex size-1.5">
        <span
          className={`absolute inline-flex h-full w-full rounded-full ${dotColor} opacity-60 ${
            status === "online" ? "animate-ping" : ""
          }`}
        />
        <span className={`relative inline-flex size-1.5 rounded-full ${dotColor}`} />
      </span>
      {label}
    </span>
  );
}
