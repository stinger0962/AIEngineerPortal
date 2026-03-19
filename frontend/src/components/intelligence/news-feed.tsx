"use client";

import Link from "next/link";
import { startTransition, useDeferredValue, useState } from "react";

import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";
import type { FeedRefreshMeta, NewsItem } from "@/lib/types/portal";

type NewsFeedProps = {
  initialItems: NewsItem[];
  initialMeta: FeedRefreshMeta;
};

export function NewsFeed({ initialItems, initialMeta }: NewsFeedProps) {
  const [items, setItems] = useState(initialItems);
  const [meta, setMeta] = useState(initialMeta);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeSaveId, setActiveSaveId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [savedOnly, setSavedOnly] = useState(false);
  const deferredSearch = useDeferredValue(search);

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      const [refreshed, refreshedMeta] = await Promise.all([portalApi.refreshNews(), portalApi.getNewsMeta()]);
      startTransition(() => {
        setItems(refreshed);
        setMeta(refreshedMeta);
      });
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleSave(newsId: number) {
    setActiveSaveId(newsId);
    try {
      const saved = await portalApi.saveNewsItem(newsId);
      startTransition(() =>
        setItems((current) => current.map((item) => (item.id === newsId ? saved : item))),
      );
    } finally {
      setActiveSaveId(null);
    }
  }

  const categories = ["all", ...new Set(items.map((item) => item.category))];
  const normalizedSearch = deferredSearch.trim().toLowerCase();
  const visibleItems = items.filter((item) => {
    const matchesCategory = category === "all" || item.category === category;
    const matchesSaved = !savedOnly || item.is_saved;
    const matchesSearch =
      !normalizedSearch ||
      item.title.toLowerCase().includes(normalizedSearch) ||
      item.summary.toLowerCase().includes(normalizedSearch) ||
      item.tags_json.some((tag) => tag.toLowerCase().includes(normalizedSearch));
    return matchesCategory && matchesSaved && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <Panel className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Items tracked</p>
              <p className="mt-2 text-3xl font-semibold text-ink">{items.length}</p>
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">High-signal updates</p>
              <p className="mt-2 text-3xl font-semibold text-ink">
                {items.filter((item) => item.signal_score >= 85).length}
              </p>
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Saved for later</p>
              <p className="mt-2 text-3xl font-semibold text-ink">{items.filter((item) => item.is_saved).length}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {isRefreshing ? "Refreshing..." : "Refresh feed"}
          </button>
        </div>
        <div className="rounded-2xl bg-white p-4 text-sm text-ink/70">
          <p>
            Feed source: <span className="font-semibold text-ink">{meta.source}</span> · Live items{" "}
            {meta.live_item_count} · Seeded items {meta.seeded_item_count}
          </p>
          <p className="mt-2">Last sync: {new Date(meta.refreshed_at).toLocaleString()}</p>
          <p className="mt-2">
            Auto-refresh {meta.auto_refresh_enabled ? "enabled" : "disabled"} · Window{" "}
            {meta.refresh_window_hours}h · Status{" "}
            <span className="font-semibold text-ink">{meta.is_stale ? "stale" : "fresh"}</span>
          </p>
        </div>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]">
          <label className="grid gap-2 text-sm text-ink/70">
            <span className="text-xs uppercase tracking-[0.24em] text-ink/50">Search</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search releases, RAG, evaluation..."
              className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-ink/30"
            />
          </label>
          <label className="grid gap-2 text-sm text-ink/70">
            <span className="text-xs uppercase tracking-[0.24em] text-ink/50">Category</span>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-ink/30"
            >
              {categories.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-end gap-3 rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink/70">
            <input
              type="checkbox"
              checked={savedOnly}
              onChange={(event) => setSavedOnly(event.target.checked)}
              className="h-4 w-4 rounded border-ink/20"
            />
            <span>Saved only</span>
          </label>
        </div>
      </Panel>

      <div className="grid gap-4">
        {visibleItems.map((item) => (
          <Panel key={item.id} className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
              <span>{item.source_name}</span>
              <span>Signal {item.signal_score}</span>
              <span>{new Date(item.published_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-2xl text-ink">{item.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{item.summary}</p>
              </div>
              {item.is_saved ? (
                <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold text-ink">Saved</span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {item.tags_json.map((tag) => (
                <span key={tag} className="rounded-full border border-ink/10 px-3 py-1 text-xs text-ink/70">
                  {tag}
                </span>
              ))}
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Why this matters</p>
              <p className="mt-2 text-sm text-ink/70">{item.why_it_matters}</p>
              <p className="mt-3 text-sm font-medium text-ink">{item.suggested_action}</p>
              <div className="mt-4 grid gap-2 md:grid-cols-3">
                <div className="rounded-2xl bg-white px-3 py-3 text-sm text-ink/75">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-ink/45">Focus area</p>
                  <p className="mt-1 font-medium text-ink">{item.focus_area}</p>
                </div>
                <div className="rounded-2xl bg-white px-3 py-3 text-sm text-ink/75">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-ink/45">Best next path</p>
                  <p className="mt-1 font-medium text-ink">{item.recommended_path_title ?? "Review in context"}</p>
                </div>
                <div className="rounded-2xl bg-white px-3 py-3 text-sm text-ink/75">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-ink/45">Best next drill</p>
                  <p className="mt-1 font-medium text-ink">{item.recommended_exercise_category ?? "general practice"}</p>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => handleSave(item.id)}
                disabled={activeSaveId === item.id || item.is_saved}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {item.is_saved ? "Saved" : activeSaveId === item.id ? "Saving..." : "Save for later"}
              </button>
              <Link
                href={item.source_url}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold"
                target="_blank"
              >
                Open source
              </Link>
              {item.recommended_path_slug ? (
                <Link
                  href={`/learn/${item.recommended_path_slug}`}
                  className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold"
                >
                  Open path
                </Link>
              ) : null}
            </div>
          </Panel>
        ))}
        {!visibleItems.length ? (
          <Panel className="text-sm text-ink/70">
            No items match the current filters yet. Try broadening the search or refreshing the feed.
          </Panel>
        ) : null}
      </div>
    </div>
  );
}
