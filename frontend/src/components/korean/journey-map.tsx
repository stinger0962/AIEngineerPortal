"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type { MapNode, MapRegion } from "@/lib/korean/types";
import { KIND_THEME, REGION_SEAL } from "@/lib/korean/theme";
import { SectionLabel, Stars } from "./ui";
import { Mascot } from "./mascot";

function NodeRow({ node, isCurrent, isLast }: { node: MapNode; isCurrent: boolean; isLast: boolean }) {
  const t = KIND_THEME[node.kind];
  const locked = node.status === "locked";
  const done = node.status === "completed";

  const medallion = locked ? (
    <span className="flex h-12 w-12 items-center justify-center rounded-full border border-ink/10 bg-sand/50 text-ink/35">
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="5" y="11" width="14" height="9" rx="2" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </svg>
    </span>
  ) : (
    <span
      className={`font-kr-serif flex h-12 w-12 items-center justify-center rounded-full text-xl ${isCurrent ? "k-current" : ""}`}
      style={{
        color: "#fff",
        background: t.accent,
        boxShadow: `0 10px 18px -8px ${t.accent}, inset 0 2px 0 rgba(255,255,255,0.35)`,
        border: "2px solid #fff",
      }}
    >
      {t.seal}
    </span>
  );

  const card = (
    <div
      className={`flex flex-1 items-center gap-3 rounded-2xl border px-4 py-3 transition-all ${
        locked ? "border-ink/8 bg-white/45 opacity-60" : "hover:-translate-y-0.5"
      }`}
      style={{
        borderColor: isCurrent ? "var(--celadon-500)" : done ? "rgba(47,111,100,0.2)" : "rgba(20,33,61,0.08)",
        background: isCurrent
          ? "linear-gradient(120deg,#e9f5f0,#ffffff)"
          : done
            ? "linear-gradient(120deg,#f1f7f4,#ffffff)"
            : locked
              ? undefined
              : "rgba(255,255,255,0.85)",
        boxShadow: isCurrent ? "0 16px 34px -18px rgba(47,111,100,0.6)" : "0 12px 26px -20px rgba(20,33,61,0.4)",
      }}
    >
      <div className="min-w-0">
        <p className="truncate font-semibold text-ink">{node.title}</p>
        <p className="text-[11px] uppercase tracking-[0.18em]" style={{ color: locked ? "rgba(20,33,61,0.35)" : t.accent }}>
          {t.label}
        </p>
      </div>
      <div className="ml-auto shrink-0 text-right">
        {done ? (
          <Stars value={node.stars} />
        ) : isCurrent ? (
          <span className="k-shine-sweep font-kr inline-flex items-center gap-1 rounded-full bg-[var(--celadon-600)] px-3.5 py-1.5 text-xs font-bold text-white shadow-[0_8px_16px_-8px_rgba(47,111,100,0.8)]">
            시작하기 <span aria-hidden>→</span>
          </span>
        ) : locked ? (
          <span className="text-[11px] uppercase tracking-[0.18em] text-ink/30">잠김</span>
        ) : (
          <span className="text-[11px] uppercase tracking-[0.18em] text-ink/45">열림</span>
        )}
      </div>
    </div>
  );

  return (
    <li className="flex gap-4">
      <div className="flex flex-col items-center">
        {medallion}
        {!isLast && (
          <span
            className="mt-1 w-[3px] flex-1 rounded-full"
            style={{ background: "repeating-linear-gradient(to bottom, var(--celadon-300) 0 5px, transparent 5px 11px)" }}
          />
        )}
      </div>
      <div className="flex-1 pb-3.5">{locked ? card : <Link href={`/korean/node/${node.slug}`}>{card}</Link>}</div>
    </li>
  );
}

export function JourneyMap() {
  const qc = useQueryClient();
  const { data: regions, isLoading } = useQuery({ queryKey: ["korean-map"], queryFn: koreanApi.getMap });
  const reset = useMutation({
    mutationFn: koreanApi.resetProgress,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["korean-map"] }),
  });

  const flat = regions?.flatMap((r) => r.nodes) ?? [];
  const currentSlug = flat.find((n) => n.status === "unlocked")?.slug;
  const cleared = flat.filter((n) => n.status === "completed").length;
  const total = flat.length || 1;
  const pct = Math.round((cleared / total) * 100);

  return (
    <div className="k-hanji k-pattern min-h-screen">
      <div className="relative mx-auto max-w-3xl px-5 py-10 sm:px-8">
        {/* header */}
        <header className="k-bounce-in mb-9">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <Mascot size={84} />
              <div>
                <SectionLabel>학 · Grow</SectionLabel>
                <h1 className="font-kr-serif mt-1 text-4xl text-ink sm:text-5xl">
                  한국어 <span className="font-display text-2xl italic text-ink/45 sm:text-3xl">Journey</span>
                </h1>
                <p className="font-kr mt-1 text-sm text-ink/55">여행하듯 배우는 한국어 — speak, listen, read your way through Korea.</p>
              </div>
            </div>
            <button
              onClick={() => {
                if (confirm("진행 상황을 모두 초기화할까요? Reset all progress? This cannot be undone.")) reset.mutate();
              }}
              className="k-press shrink-0 rounded-full border border-ink/12 bg-white/60 px-3 py-1.5 text-xs text-ink/55 hover:text-ink"
            >
              초기화 · Reset
            </button>
          </div>

          {!isLoading && (
            <div className="mt-5">
              <div className="mb-1.5 flex items-center justify-between text-xs text-ink/50">
                <span className="font-medium">{cleared} / {total} cleared</span>
                <span>{pct}%</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-ink/8">
                <div
                  className="k-shine-sweep h-full rounded-full transition-[width] duration-700"
                  style={{ width: `${pct}%`, background: "linear-gradient(90deg,var(--celadon-500),var(--celadon-600))" }}
                />
              </div>
            </div>
          )}
        </header>

        {isLoading ? (
          <p className="font-kr text-sm text-ink/40">불러오는 중…</p>
        ) : (
          <div className="space-y-7">
            {regions?.map((r, ri) => {
              const rCleared = r.nodes.filter((n) => n.status === "completed").length;
              return (
                <section key={r.slug} className="k-bounce-in" style={{ animationDelay: `${ri * 90}ms` }}>
                  {/* colored region banner */}
                  <div
                    className="flex items-center gap-4 rounded-3xl rounded-b-none border border-b-0 px-5 py-4"
                    style={{
                      background: "linear-gradient(105deg, rgba(95,179,163,0.22), rgba(95,179,163,0.05))",
                      borderColor: "rgba(95,179,163,0.3)",
                    }}
                  >
                    <span className="font-kr-serif flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--celadon-300)] bg-white/80 text-2xl text-[var(--celadon-700)] shadow-[0_6px_14px_-8px_rgba(47,111,100,0.6)]">
                      {REGION_SEAL[r.theme] ?? "✦"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--celadon-700)]">Stage {ri + 1}</p>
                      <h2 className="font-kr-serif truncate text-xl text-ink">{r.title}</h2>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {r.nodes.map((n, i) => (
                        <span
                          key={i}
                          className="h-2 w-2 rounded-full"
                          style={{ background: n.status === "completed" ? "var(--celadon-600)" : "rgba(20,33,61,0.14)" }}
                        />
                      ))}
                      <span className="ml-1 text-xs font-medium text-ink/50">{rCleared}/{r.nodes.length}</span>
                    </div>
                  </div>

                  {/* nodes */}
                  <ul className="rounded-3xl rounded-t-none border border-t-0 border-ink/8 bg-white/55 p-5 backdrop-blur">
                    {r.nodes.map((n, i) => (
                      <NodeRow key={n.slug} node={n} isCurrent={n.slug === currentSlug} isLast={i === r.nodes.length - 1} />
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
