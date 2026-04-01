"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Briefcase, FileText, Gauge, GraduationCap, Menu, MessageSquare, Search, Settings, SquareTerminal, BookOpen, X } from "lucide-react";

const items = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/learn", label: "Learn", icon: GraduationCap },
  { href: "/practice", label: "Practice", icon: SquareTerminal },
  { href: "/review", label: "Review", icon: Brain },
  { href: "/interview", label: "Interview", icon: BookOpen },
  { href: "/projects", label: "Portfolio", icon: Briefcase },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/jobs/live", label: "Jobs", icon: Search },
  { href: "/copilot", label: "Copilot", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function SidebarNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const navLinks = items.map(({ href, label, icon: Icon }) => {
    const isActive =
      href === "/"
        ? pathname === "/"
        : pathname === href || pathname.startsWith(href + "/");
    return (
      <Link
        key={href}
        href={href === "/practice" ? "/practice/python" : href}
        onClick={() => setOpen(false)}
        className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${
          isActive
            ? "bg-ember/20 text-ember font-medium"
            : "text-cream/80 hover:bg-white/10 hover:text-white"
        }`}
      >
        <Icon size={18} />
        {label}
      </Link>
    );
  });

  return (
    <>
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between bg-ink px-4 py-3">
        <span className="text-sm font-semibold text-cream uppercase tracking-wide">AI Portal</span>
        <button onClick={() => setOpen(!open)} className="text-cream p-1">
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile menu overlay */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40 bg-ink pt-16 px-6 py-8 overflow-y-auto">
          <nav className="space-y-2">
            {navLinks}
          </nav>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-72 flex-col justify-between border-r border-white/40 bg-ink px-6 py-8 text-cream lg:flex">
        <div className="space-y-8">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.32em] text-cream/60">AI Engineer Portal</p>
            <h1 className="font-display text-3xl leading-tight">Career transition, organized like a product.</h1>
          </div>
          <nav className="space-y-2">
            {items.map(({ href, label, icon: Icon }) => {
              const isActive =
                href === "/"
                  ? pathname === "/"
                  : pathname === href || pathname.startsWith(href + "/");
              return (
                <Link
                  key={href}
                  href={href === "/practice" ? "/practice/python" : href}
                  className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${
                    isActive
                      ? "bg-ember/20 text-ember font-medium"
                      : "text-cream/80 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <Icon size={18} />
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 text-sm text-cream/75">
          Focus the portal on Python depth, shipping projects, evaluation, and portfolio readiness.
        </div>
      </aside>
    </>
  );
}
