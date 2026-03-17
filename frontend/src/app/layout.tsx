import type { Metadata } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Engineer Portal",
  description: "Personal AI engineer transition operating system",
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
