import { setRequestLocale, getTranslations } from "next-intl/server";

import { StatusBoard } from "@/components/status/status-board";

export default async function StatusPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Status");

  return (
    <section className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-16 lg:py-24">
      <div className="max-w-3xl space-y-4 mb-14">
        <span className="font-mono text-xs uppercase tracking-wide text-[color:var(--muted)]">
          /status
        </span>
        <h1 className="text-4xl md:text-5xl lg:text-6xl tracking-tighter leading-[0.95] font-medium">
          {t("title")}
        </h1>
        <p className="text-base text-[color:var(--muted)] leading-relaxed max-w-[55ch]">
          {t("subtitle")}
        </p>
      </div>
      <StatusBoard />
    </section>
  );
}
