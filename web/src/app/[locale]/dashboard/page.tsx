import { DiscordLogoIcon } from "@phosphor-icons/react/dist/ssr";
import { setRequestLocale, getTranslations } from "next-intl/server";

import { DashboardPreview } from "@/components/dashboard/dashboard-preview";

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Dashboard");

  return (
    <section className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-16 lg:py-24 space-y-16">
      <div className="grid gap-10 lg:grid-cols-12 lg:items-end">
        <div className="lg:col-span-7 space-y-4">
          <span className="font-mono text-xs uppercase tracking-wide text-[color:var(--muted)]">
            /dashboard · preview
          </span>
          <h1 className="text-4xl md:text-5xl lg:text-6xl tracking-tighter leading-[0.95] font-medium">
            {t("comingSoon.title")}
          </h1>
          <p className="text-base text-[color:var(--muted)] leading-relaxed max-w-[60ch]">
            {t("comingSoon.body")}
          </p>
        </div>

        <aside className="lg:col-span-5 rounded-2xl border border-[color:var(--border)] p-6 space-y-4">
          <h2 className="text-base font-medium tracking-tight">
            {t("loginRequired.title")}
          </h2>
          <p className="text-sm text-[color:var(--muted)] leading-relaxed">
            {t("loginRequired.body")}
          </p>
          <button
            type="button"
            disabled
            className="w-full inline-flex items-center justify-center gap-2 h-10 px-5 rounded-full bg-[color:var(--foreground)]/10 text-[color:var(--muted)] text-sm font-medium cursor-not-allowed"
          >
            <DiscordLogoIcon className="size-4" weight="fill" />
            {t("loginRequired.cta")}
          </button>
          <p className="text-xs text-[color:var(--muted)] leading-relaxed">
            {t("loginRequired.note")}
          </p>
        </aside>
      </div>

      <DashboardPreview />
    </section>
  );
}
