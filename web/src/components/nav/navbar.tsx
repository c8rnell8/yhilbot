"use client";

import { motion } from "framer-motion";
import {
  DiscordLogoIcon,
  GithubLogoIcon,
  ListIcon,
  XIcon,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { LanguageSwitcher } from "@/components/nav/language-switcher";
import { Link, usePathname } from "@/i18n/navigation";

const NAV_ITEMS = [
  { key: "home", href: "/" as const },
  { key: "status", href: "/status" as const },
  { key: "dashboard", href: "/dashboard" as const },
  { key: "editor", href: "/editor" as const },
];

export function Navbar() {
  const t = useTranslations("Nav");
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[color:var(--background)]/70 border-b border-[color:var(--border)]">
      <nav
        aria-label="Primary"
        className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-10 h-16 flex items-center gap-6"
      >
        <Link
          href="/"
          className="flex items-center gap-2.5 group"
          aria-label="yhilbot"
        >
          <Logo className="size-7 text-[color:var(--foreground)] transition-transform group-hover:rotate-3" />
          <span className="font-mono text-sm tracking-tight">yhilbot</span>
        </Link>

        <div className="hidden md:flex items-center gap-1 ml-4">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.key}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className="relative px-3 py-2 text-sm text-[color:var(--muted)] hover:text-[color:var(--foreground)] transition-colors"
              >
                {t(item.key)}
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-x-3 -bottom-px h-px bg-[color:var(--foreground)]"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </Link>
            );
          })}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher />
          <a
            href="https://github.com/c8rnell8/yhilbot"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t("github")}
            className="hidden sm:inline-flex size-9 items-center justify-center rounded-full text-[color:var(--muted)] hover:text-[color:var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <GithubLogoIcon className="size-5" weight="regular" />
          </a>
          <a
            href="https://discord.com/oauth2/authorize"
            target="_blank"
            rel="noopener noreferrer"
            className="group hidden sm:inline-flex items-center gap-2 px-4 h-9 rounded-full bg-[color:var(--foreground)] text-[color:var(--background)] text-sm font-medium transition-transform active:scale-[0.97]"
          >
            <DiscordLogoIcon className="size-4" weight="fill" />
            <span>{t("addToDiscord")}</span>
          </a>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            className="md:hidden inline-flex size-9 items-center justify-center rounded-full text-[color:var(--muted)] hover:text-[color:var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            {open ? (
              <XIcon className="size-5" weight="regular" />
            ) : (
              <ListIcon className="size-5" weight="regular" />
            )}
          </button>
        </div>
      </nav>

      {open && (
        <div
          id="mobile-nav"
          className="md:hidden border-t border-[color:var(--border)] px-4 py-4 flex flex-col gap-1"
        >
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              onClick={() => setOpen(false)}
              className="px-2 py-2 rounded-md text-sm text-[color:var(--muted)] hover:text-[color:var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5"
            >
              {t(item.key)}
            </Link>
          ))}
          <a
            href="https://discord.com/oauth2/authorize"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center justify-center gap-2 px-4 h-10 rounded-full bg-[color:var(--foreground)] text-[color:var(--background)] text-sm font-medium"
          >
            <DiscordLogoIcon className="size-4" weight="fill" />
            <span>{t("addToDiscord")}</span>
          </a>
        </div>
      )}
    </header>
  );
}

function Logo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <rect x="2" y="6" width="28" height="20" rx="4" stroke="currentColor" strokeWidth="2" />
      <path d="M10 13 L14 16 L10 19 Z" fill="currentColor" />
      <rect x="16" y="14" width="8" height="4" rx="1" fill="currentColor" />
    </svg>
  );
}
