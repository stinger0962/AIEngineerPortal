import type { Metadata } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://portal.leipan.cc"),
  title: {
    default: "AI Engineer Portal",
    template: "%s · AI Engineer Portal",
  },
  description: "Personal AI engineer transition operating system",
  openGraph: {
    type: "website",
    siteName: "AI Engineer Portal",
    locale: "zh_CN",
    title: "AI Engineer Portal",
    description: "Personal AI engineer transition operating system",
  },
  twitter: {
    card: "summary",
    title: "AI Engineer Portal",
    description: "Personal AI engineer transition operating system",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
