"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Briefcase, Compass, FileText, GraduationCap, Home, Menu, MessageSquare, Mic, Scroll, Search, Settings, Sparkles, SquareTerminal, BookOpen, Wrench, X } from "lucide-react";

type NavItem = { href: string; label: string; icon: LucideIcon };
type NavGroup = { key: string; label: string; accent: string; items: NavItem[] };

// 方寸 · 三域门户：首页(屏风) → 学(成长) → 造(蒸馏) → 玄(命理) → 系统
const groups: NavGroup[] = [
  {
    key: "home",
    label: "方寸",
    accent: "#cdbd8e",
    items: [{ href: "/", label: "屏风 · 首页", icon: Home }],
  },
  {
    key: "xue",
    label: "学 · Grow",
    accent: "#5fb3a3",
    items: [
      { href: "/grow", label: "学域总览", icon: Compass },
      { href: "/learn", label: "Learn", icon: GraduationCap },
      { href: "/practice", label: "Practice", icon: SquareTerminal },
      { href: "/review", label: "Review", icon: Brain },
      { href: "/interview", label: "Interview", icon: BookOpen },
      { href: "/projects", label: "Portfolio", icon: Briefcase },
      { href: "/resume", label: "Resume", icon: FileText },
      { href: "/jobs/live", label: "Jobs", icon: Search },
      { href: "/copilot", label: "Copilot", icon: MessageSquare },
    ],
  },
  {
    key: "zao",
    label: "造 · Distill",
    accent: "#e08a3c",
    items: [
      { href: "/toolkits", label: "蒸馏所", icon: Wrench },
      { href: "/toolkits/dub", label: "配 · Dub", icon: Mic },
    ],
  },
  {
    key: "xuan",
    label: "玄 · Oracle",
    accent: "#9a7bf0",
    items: [
      { href: "/ziwei", label: "紫微斗数", icon: Sparkles },
      { href: "/qian", label: "灵签", icon: Scroll },
    ],
  },
  {
    key: "sys",
    label: "系统",
    accent: "#8a8170",
    items: [{ href: "/settings", label: "Settings", icon: Settings }],
  },
];

function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/grow") return pathname === "/grow";
  if (href === "/toolkits") return pathname === "/toolkits";
  return pathname === href || pathname.startsWith(href + "/");
}

function resolveHref(href: string): string {
  return href === "/practice" ? "/practice/python" : href;
}

export function SidebarNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const renderGroups = (onNavigate?: () => void) =>
    groups.map((group) => (
      <div key={group.key} className="space-y-1.5">
        <p
          className="px-4 pt-1 text-[10px] font-semibold uppercase tracking-[0.28em]"
          style={{ color: group.accent }}
        >
          {group.label}
        </p>
        {group.items.map(({ href, label, icon: Icon }) => {
          const active = isActivePath(pathname, href);
          return (
            <Link
              key={href}
              href={resolveHref(href)}
              onClick={onNavigate}
              className={`flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm transition ${
                active
                  ? "bg-ember/20 text-ember font-medium"
                  : "text-cream/80 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </div>
    ));

  return (
    <>
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between bg-ink px-4 py-3">
        <span className="text-sm font-semibold text-cream uppercase tracking-wide">方寸 Portal</span>
        <button onClick={() => setOpen(!open)} className="text-cream p-1" aria-label={open ? "Close menu" : "Open menu"}>
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile menu overlay */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40 bg-ink pt-16 px-6 py-8 overflow-y-auto">
          <nav className="space-y-5">{renderGroups(() => setOpen(false))}</nav>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-72 flex-col justify-between border-r border-white/40 bg-ink px-6 py-8 text-cream lg:flex">
        <div className="space-y-7 overflow-y-auto pr-1">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.32em] text-cream/60">方寸 · 三域门户</p>
            <h1 className="font-display text-3xl leading-tight">学 · 造 · 玄，一处掌管。</h1>
          </div>
          <nav className="space-y-5">{renderGroups()}</nav>
        </div>
        <div className="mt-4 rounded-[24px] border border-white/10 bg-white/5 p-4 text-sm text-cream/75">
          学练造研，玄机自取。一个人的操作系统。
        </div>
      </aside>
    </>
  );
}
