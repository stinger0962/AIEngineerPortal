"use client";

import { usePathname } from "next/navigation";

import { ConditionalHeader } from "@/components/layout/conditional-header";
import { DomainShell, type DomainConfig } from "@/components/layout/domain-shell";
import { SidebarNav } from "@/components/layout/sidebar-nav";

// 造 · 蒸馏所 silo — warm copper accent.
const ZAO: DomainConfig = {
  wordmark: "蒸馏所 · 造",
  accent: "#bf6a1e",
  links: [
    { label: "蒸馏所", href: "/toolkits" },
    { label: "炼", href: "/toolkits/podcast" },
    { label: "织", href: "/toolkits/summarize" },
    { label: "录", href: "/toolkits/scribe" },
    { label: "配", href: "/toolkits/dub" },
  ],
};

// 玄 · 命理 silo — violet accent (deepened for contrast on the light strip).
const XUAN: DomainConfig = {
  wordmark: "命理 · 玄",
  accent: "#7c5cf0",
  links: [
    { label: "命理", href: "/xuan" },
    { label: "紫微斗数", href: "/ziwei" },
    { label: "灵签", href: "/qian" },
  ],
};

function inDomain(pathname: string, root: string): boolean {
  return pathname === root || pathname.startsWith(root + "/");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Full-bleed immersive routes — no chrome at all.
  // / = 屏风 hub homepage; /xuan = 命理 · 玄 domain landing.
  if (pathname === "/" || pathname === "/xuan") {
    return <div className="min-h-screen">{children}</div>;
  }

  // Domain silos — slim top strip, no cross-domain sidebar.
  if (inDomain(pathname, "/toolkits")) {
    return <DomainShell config={ZAO}>{children}</DomainShell>;
  }
  if (inDomain(pathname, "/ziwei") || inDomain(pathname, "/qian")) {
    return <DomainShell config={XUAN}>{children}</DomainShell>;
  }

  // 学 · Grow + system — the legacy sidebar shell (its own independent silo).
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(247,127,0,0.18),_transparent_24%),linear-gradient(135deg,_#f8f3e8,_#eef5f1_58%,_#f7efe5)] text-ink">
      <div className="mx-auto flex max-w-[1600px]">
        <SidebarNav />
        <main className="min-h-screen flex-1 px-4 py-4 pt-16 lg:px-8 lg:py-6 lg:pt-6">
          <div className="space-y-8">
            <ConditionalHeader />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
