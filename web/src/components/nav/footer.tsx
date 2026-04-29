import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export function Footer() {
  const t = useTranslations("Footer");
  const tNav = useTranslations("Nav");

  return (
    <footer className="border-t border-[color:var(--border)] mt-24">
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 py-10 grid gap-8 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 items-start">
        <div className="space-y-2">
          <p className="font-mono text-sm tracking-tight">yhilbot</p>
          <p className="text-sm text-[color:var(--muted)] max-w-[40ch]">
            {t("tagline")}
          </p>
          <p className="text-xs text-[color:var(--muted)] pt-2">
            {t("rights")}
          </p>
        </div>

        <nav aria-label="Footer">
          <ul className="text-sm space-y-2">
            {(["home", "status", "dashboard", "editor"] as const).map((k) => (
              <li key={k}>
                <Link
                  href={k === "home" ? "/" : `/${k}`}
                  className="text-[color:var(--muted)] hover:text-[color:var(--foreground)] transition-colors"
                >
                  {tNav(k)}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <ul className="text-sm space-y-2">
          <li>
            <a
              href="https://github.com/c8rnell8/yhilbot"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[color:var(--muted)] hover:text-[color:var(--foreground)] transition-colors"
            >
              {t("links.code")}
            </a>
          </li>
          <li>
            <a
              href="https://github.com/c8rnell8/yhilbot/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[color:var(--muted)] hover:text-[color:var(--foreground)] transition-colors"
            >
              {t("links.issues")}
            </a>
          </li>
          <li>
            <a
              href="https://github.com/c8rnell8/yhilbot/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[color:var(--muted)] hover:text-[color:var(--foreground)] transition-colors"
            >
              {t("links.license")}
            </a>
          </li>
        </ul>

        <div className="font-mono text-xs text-[color:var(--muted)] space-y-1">
          <p>ffmpeg · discord.py · next.js</p>
          <p>v5.2 · 2026</p>
        </div>
      </div>
    </footer>
  );
}
