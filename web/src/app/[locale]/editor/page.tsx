import { ArrowLeftIcon, CheckIcon } from "@phosphor-icons/react/dist/ssr";
import { setRequestLocale, getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

export default async function EditorPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Editor");

  const items = (t.raw("demo.items") ?? []) as ReadonlyArray<string>;

  return (
    <section className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-16 lg:py-24">
      <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
        <div className="lg:col-span-6 space-y-6">
          <span className="inline-flex items-center gap-2 px-3 h-7 rounded-full border border-[color:var(--border)] text-[11px] font-mono uppercase tracking-wide text-[color:var(--muted)]">
            {t("comingSoon")}
          </span>
          <h1 className="text-4xl md:text-5xl lg:text-6xl tracking-tighter leading-[0.95] font-medium">
            {t("title")}
          </h1>
          <p className="text-base md:text-lg text-[color:var(--muted)] leading-relaxed max-w-[55ch]">
            {t("subtitle")}
          </p>
          <p className="text-sm text-[color:var(--muted)] leading-relaxed max-w-[60ch] border-l border-[color:var(--border)] pl-4">
            {t("explainer")}
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 h-10 px-4 rounded-full border border-[color:var(--border)] text-sm hover:border-[color:var(--foreground)]/40 transition-colors"
          >
            <ArrowLeftIcon className="size-4" weight="bold" />
            {t("back")}
          </Link>
        </div>

        <div className="lg:col-span-6">
          <div className="rounded-2xl border border-[color:var(--border)] p-6 lg:p-8 space-y-5">
            <h2 className="text-xs uppercase tracking-wide text-[color:var(--muted)] font-mono">
              {t("demo.title")}
            </h2>
            <ul className="space-y-3">
              {items.map((item, idx) => (
                <li key={idx} className="flex gap-3 items-start">
                  <span className="mt-0.5 inline-flex size-5 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                    <CheckIcon className="size-3" weight="bold" aria-hidden />
                  </span>
                  <span className="text-sm leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>

            <div className="pt-4 border-t border-[color:var(--border)] grid grid-cols-3 gap-3 text-[11px] font-mono text-[color:var(--muted)] uppercase tracking-wide">
              {[
                ["space", "play / pause"],
                ["S", "split @ cursor"],
                ["T", "text overlay"],
                ["[ ]", "trim in / out"],
                ["⌘ Z", "undo"],
                ["⌘⇧ Z", "redo"],
              ].map(([k, v]) => (
                <div key={k as string} className="rounded-md border border-[color:var(--border)] p-2">
                  <span className="text-[color:var(--foreground)] font-mono">{k}</span>
                  <span className="block text-[10px] mt-0.5">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
