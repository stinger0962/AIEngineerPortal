import { paidProduct, productName } from "@/lib/product/config";

import type { Metadata } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { ChunkErrorReloader } from "@/components/system/chunk-error-reloader";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || (paidProduct ? "http://localhost:3001" : "https://portal.leipan.cc")),
  title: {
    default: productName,
    template: `%s · ${productName}`,
  },
  description: paidProduct ? "紫微斗数、灵签与更多文化探索体验" : "Personal AI engineer transition operating system",
  openGraph: {
    type: "website",
    siteName: productName,
    locale: "zh_CN",
    title: productName,
    description: paidProduct ? "紫微斗数、灵签与更多文化探索体验" : "Personal AI engineer transition operating system",
  },
  twitter: {
    card: "summary",
    title: productName,
    description: paidProduct ? "紫微斗数、灵签与更多文化探索体验" : "Personal AI engineer transition operating system",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang={paidProduct ? "zh-Hans" : "en"}>
      <body>
        <ChunkErrorReloader />
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
