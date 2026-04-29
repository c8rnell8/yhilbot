import { setRequestLocale } from "next-intl/server";

import { Commands } from "@/components/landing/commands";
import { Features } from "@/components/landing/features";
import { Hero } from "@/components/landing/hero";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <Hero />
      <Commands />
      <Features />
    </>
  );
}
