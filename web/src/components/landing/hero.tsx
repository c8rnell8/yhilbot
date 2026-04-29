"use client";

import { motion } from "framer-motion";
import {
  ArrowRightIcon,
  DiscordLogoIcon,
  PlayIcon,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { StatusPill } from "@/components/ui/status-pill";

export function Hero() {
  const t = useTranslations("Hero");

  return (
    <section
      aria-labelledby="hero-title"
      className="relative overflow-hidden border-b border-[color:var(--border)]"
    >
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 pt-20 pb-24 lg:pt-28 lg:pb-32 grid gap-12 lg:grid-cols-12 lg:items-center">
        <div className="lg:col-span-7 space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap items-center gap-3"
          >
            <span className="font-mono text-xs tracking-wide text-[color:var(--muted)] uppercase">
              {t("eyebrow")}
            </span>
            <StatusPill />
          </motion.div>

          <motion.h1
            id="hero-title"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl md:text-6xl lg:text-7xl tracking-tighter leading-[0.95] font-medium"
          >
            {t("title")}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="text-lg md:text-xl text-[color:var(--muted)] leading-relaxed max-w-[58ch]"
          >
            {t("subtitle")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap gap-3"
          >
            <a
              href="https://discord.com/oauth2/authorize"
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex items-center gap-2 h-11 px-5 rounded-full bg-[color:var(--foreground)] text-[color:var(--background)] text-sm font-medium transition-transform active:scale-[0.97]"
            >
              <DiscordLogoIcon className="size-4" weight="fill" />
              {t("ctaPrimary")}
              <ArrowRightIcon
                className="size-4 transition-transform group-hover:translate-x-0.5"
                weight="bold"
              />
            </a>
            <Link
              href="/editor"
              className="group inline-flex items-center gap-2 h-11 px-5 rounded-full border border-[color:var(--border)] text-sm font-medium hover:border-[color:var(--foreground)]/40 transition-colors"
            >
              <PlayIcon className="size-4" weight="fill" />
              {t("ctaSecondary")}
            </Link>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-5"
        >
          <HeroPreview />
        </motion.div>
      </div>
    </section>
  );
}

function HeroPreview() {
  return (
    <div
      className="relative rounded-2xl border border-[color:var(--border)] bg-[color:var(--background)] p-1 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.25)]"
      aria-hidden
    >
      <div className="rounded-xl overflow-hidden bg-zinc-950 text-zinc-200 font-mono text-[12.5px] leading-relaxed">
        <div className="flex items-center gap-1.5 px-3.5 py-2.5 border-b border-white/5">
          <span className="size-2.5 rounded-full bg-rose-500/60" />
          <span className="size-2.5 rounded-full bg-amber-500/60" />
          <span className="size-2.5 rounded-full bg-emerald-500/60" />
          <span className="ml-3 text-[11px] text-zinc-500 tracking-wide">
            #general · yhilbot
          </span>
        </div>
        <div className="p-4 space-y-3">
          <Line user="@you" tone="zinc">
            /edit
          </Line>
          <Line user="yhilbot" tone="accent">
            QUAD Editor opened. cursor at 00:00.00
          </Line>
          <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500">
              timeline
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full w-2/5 bg-emerald-500/70 rounded-full" />
              </div>
              <span className="text-[11px] text-zinc-400 font-mono">00:04.20</span>
            </div>
            <div className="grid grid-cols-5 gap-1.5 text-[10px] text-zinc-300">
              {[
                "split",
                "text",
                "speed",
                "fps",
                "render",
              ].map((label) => (
                <span
                  key={label}
                  className="rounded-md border border-white/10 bg-white/[0.03] py-1 text-center font-mono uppercase tracking-wide"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
          <Line user="@you" tone="zinc">
            split @ 04.20
          </Line>
          <Line user="yhilbot" tone="accent">
            ok. clip[0] = 00:00–04.20  /  clip[1] = 04.20–10.00
          </Line>
          <Line user="@you" tone="zinc">
            /text &quot;ON GOD&quot; t=2.5–4.0 color=#10b981
          </Line>
          <Line user="yhilbot" tone="accent">
            overlay added. preview rendered (~6.4 mb)
          </Line>
        </div>
      </div>
    </div>
  );
}

function Line({
  user,
  tone,
  children,
}: {
  user: string;
  tone: "zinc" | "accent";
  children: React.ReactNode;
}) {
  const userClass = tone === "accent" ? "text-emerald-400" : "text-zinc-300";
  return (
    <div className="flex gap-3">
      <span className={`${userClass} shrink-0`}>{user}</span>
      <span className="text-zinc-300">{children}</span>
    </div>
  );
}
