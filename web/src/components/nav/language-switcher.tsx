"use client";

import { CaretDownIcon, GlobeIcon } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { usePathname, useRouter } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";

const LABELS: Record<Locale, string> = {
  en: "EN",
  uk: "UK",
  ru: "RU",
};

const LONG_LABELS: Record<Locale, string> = {
  en: "English",
  uk: "Українська",
  ru: "Русский",
};

export function LanguageSwitcher() {
  const t = useTranslations("Nav");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();

  function onSelect(next: Locale) {
    if (next === locale) return;
    startTransition(() => {
      router.replace(pathname, { locale: next });
    });
  }

  return (
    <div className="relative inline-flex items-center">
      <label htmlFor="lang-switch" className="sr-only">
        {t("languageLabel")}
      </label>
      <GlobeIcon
        className="absolute left-2 size-4 text-[color:var(--muted)] pointer-events-none"
        aria-hidden
      />
      <select
        id="lang-switch"
        value={locale}
        onChange={(e) => onSelect(e.target.value as Locale)}
        disabled={pending}
        className="appearance-none pl-7 pr-7 h-9 rounded-full text-sm bg-transparent border border-[color:var(--border)] text-[color:var(--foreground)] hover:border-[color:var(--foreground)]/40 transition-colors disabled:opacity-50 cursor-pointer"
      >
        {routing.locales.map((l) => (
          <option key={l} value={l} className="bg-[color:var(--background)]">
            {LABELS[l as Locale]} — {LONG_LABELS[l as Locale]}
          </option>
        ))}
      </select>
      <CaretDownIcon
        className="absolute right-2 size-3 text-[color:var(--muted)] pointer-events-none"
        weight="bold"
        aria-hidden
      />
    </div>
  );
}
