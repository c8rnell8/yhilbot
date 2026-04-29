"use client";

import { motion } from "framer-motion";
import {
  ArrowsClockwiseIcon,
  DatabaseIcon,
  GitForkIcon,
  LightningIcon,
  ShieldCheckIcon,
  TranslateIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

type FeatureKey =
  | "security"
  | "concurrency"
  | "cache"
  | "sessions"
  | "i18n"
  | "open";

const ITEMS: ReadonlyArray<{ key: FeatureKey; Icon: Icon }> = [
  { key: "security", Icon: ShieldCheckIcon },
  { key: "concurrency", Icon: LightningIcon },
  { key: "cache", Icon: ArrowsClockwiseIcon },
  { key: "sessions", Icon: DatabaseIcon },
  { key: "i18n", Icon: TranslateIcon },
  { key: "open", Icon: GitForkIcon },
];

export function Features() {
  const t = useTranslations("Features");

  return (
    <section
      aria-labelledby="features-title"
      className="border-b border-[color:var(--border)]"
    >
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-24 lg:py-32">
        <div className="max-w-3xl space-y-4">
          <span className="font-mono text-xs uppercase tracking-wide text-[color:var(--muted)]">
            002 / Engineering
          </span>
          <h2
            id="features-title"
            className="text-4xl md:text-5xl lg:text-6xl tracking-tighter leading-[0.95] font-medium"
          >
            {t("title")}
          </h2>
          <p className="text-base text-[color:var(--muted)] leading-relaxed max-w-[55ch]">
            {t("subtitle")}
          </p>
        </div>

        <div className="mt-14 grid gap-x-10 gap-y-12 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {ITEMS.map(({ key, Icon }, idx) => (
            <motion.article
              key={key}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{
                duration: 0.45,
                delay: (idx % 3) * 0.05,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="space-y-3 border-t border-[color:var(--border)] pt-6"
            >
              <Icon
                className="size-5 text-[color:var(--foreground)]"
                weight="regular"
                aria-hidden
              />
              <h3 className="text-lg font-medium tracking-tight">
                {t(`items.${key}.title`)}
              </h3>
              <p className="text-sm text-[color:var(--muted)] leading-relaxed max-w-[42ch]">
                {t(`items.${key}.body`)}
              </p>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
