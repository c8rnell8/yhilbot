import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  // The actual <html> shell is rendered by [locale]/layout.tsx — this
  // root layout is required by Next but does not render its own boundary.
  return children;
}
