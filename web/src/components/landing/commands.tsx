"use client";

import { motion } from "framer-motion";
import {
  ChartLineUpIcon,
  FilmReelIcon,
  ImageIcon,
  PencilLineIcon,
  QuestionIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

type Cmd = {
  key: "gif" | "caption" | "edit" | "stats" | "help";
  Icon: Icon;
};

const COMMANDS: ReadonlyArray<Cmd> = [
  { key: "gif", Icon: FilmReelIcon },
  { key: "caption", Icon: ImageIcon },
  { key: "edit", Icon: PencilLineIcon },
  { key: "stats", Icon: ChartLineUpIcon },
  { key: "help", Icon: QuestionIcon },
];

export function Commands() {
  const t = useTranslations("Commands");

  return (
    <section
      id="commands"
      aria-labelledby="commands-title"
      className="border-b border-[color:var(--border)]"
    >
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-24 lg:py-32">
        <div className="grid gap-12 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-5 space-y-4">
            <span className="font-mono text-xs uppercase tracking-wide text-[color:var(--muted)]">
              001 / Commands
            </span>
            <h2
              id="commands-title"
              className="text-4xl md:text-5xl lg:text-6xl tracking-tighter leading-[0.95] font-medium"
            >
              {t("title")}
            </h2>
            <p className="text-base text-[color:var(--muted)] leading-relaxed max-w-[55ch]">
              {t("subtitle")}
            </p>
          </div>
          <div className="lg:col-span-7 hidden lg:block">
            <div className="font-mono text-xs uppercase tracking-wide text-[color:var(--muted)] pb-3 border-b border-[color:var(--border)] flex justify-between">
              <span>command</span>
              <span>summary</span>
            </div>
          </div>
        </div>

        <ul role="list" className="mt-10 grid gap-px border border-[color:var(--border)] bg-[color:var(--border)] rounded-2xl overflow-hidden">
          {COMMANDS.map(({ key, Icon }, idx) => (
            <motion.li
              key={key}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{
                duration: 0.45,
                delay: idx * 0.05,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="bg-[color:var(--background)] grid grid-cols-1 lg:grid-cols-12 gap-6 px-6 py-7 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
            >
              <div className="lg:col-span-3 flex items-center gap-3">
                <span className="inline-flex size-9 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <Icon className="size-4.5" weight="regular" />
                </span>
                <span className="font-mono text-base tracking-tight">
                  {t(`items.${key}.name`)}
                </span>
              </div>
              <div className="lg:col-span-4 flex items-center text-sm text-[color:var(--foreground)]">
                {t(`items.${key}.summary`)}
              </div>
              <div className="lg:col-span-5 flex items-center text-sm text-[color:var(--muted)] leading-relaxed">
                {t(`items.${key}.detail`)}
              </div>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
