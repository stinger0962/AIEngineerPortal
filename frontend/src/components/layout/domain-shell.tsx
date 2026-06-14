"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Silo chrome for a single domain (造 / 玄). Replaces the global cross-domain
// sidebar with a slim top strip: ← back to 方寸 首页, the domain wordmark, and
// ONLY that domain's own links. You can't hop to other domains from here — the
// way out is 首页. Keeps the light page background so existing light-themed
// pages (toolkits, ziwei, qian) render unchanged; the domain identity comes
// through the accent color on the strip.

export type DomainLink = { label: string; href: string };

export type DomainConfig = {
  wordmark: string; // e.g. "蒸馏所 · 造"
  accent: string; // hex — strip wordmark + active link color
  links: DomainLink[];
};

export function DomainShell({ config, children }: { config: DomainConfig; children: React.ReactNode }) {
  const pathname = usePathname();
  const active = (href: string) => pathname === href;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(247,127,0,0.16),_transparent_24%),linear-gradient(135deg,_#f8f3e8,_#eef5f1_58%,_#f7efe5)] text-ink">
      {/* Top strip */}
      <header className="sticky top-0 z-30 border-b border-ink/10 bg-white/75 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-4 py-3 lg:px-8">
          <Link
            href="/"
            className="flex shrink-0 items-center gap-1.5 text-[13px] text-ink/55 transition-colors hover:text-ink"
          >
            <span aria-hidden="true">←</span> 方寸
          </Link>

          <span
            aria-hidden="true"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[5px] text-[13px] text-[#f3e6cf]"
            style={{ background: "#b9472f", fontFamily: "'Songti SC','SimSun',serif" }}
          >
            磊
          </span>

          <span
            className="shrink-0 text-[15px] tracking-[0.18em]"
            style={{ color: config.accent, fontFamily: "'Songti SC','Noto Serif CJK SC','SimSun',serif" }}
          >
            {config.wordmark}
          </span>

          <nav className="ml-auto flex items-center gap-1 overflow-x-auto">
            {config.links.map((l) => {
              const on = active(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className="shrink-0 rounded-full px-3 py-1.5 text-[13px] transition-colors"
                  style={
                    on
                      ? { color: config.accent, background: `${config.accent}1a`, fontWeight: 500 }
                      : { color: "rgba(43,38,31,0.6)" }
                  }
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto min-h-[calc(100vh-57px)] max-w-[1600px] px-4 py-5 lg:px-8 lg:py-7">
        {children}
      </main>
    </div>
  );
}
