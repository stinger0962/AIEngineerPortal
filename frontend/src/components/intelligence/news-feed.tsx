"use client";

import Link from "next/link";
import { startTransition, useState } from "react";

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
              <p className="mt-2 text-3xl font-semibold text-ink">{items.filter((item) => item.signal_score >= 85).length}</p>
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
            Feed source: <span className="font-semibold text-ink">{meta.source}</span> · Live items {meta.live_item_count} · Seeded items {meta.seeded_item_count}
          </p>
          <p className="mt-2">Last sync: {new Date(meta.refreshed_at).toLocaleString()}</p>
        </div>
      </Panel>

      <div className="grid gap-4">
        {items.map((item) => (
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
              {item.is_saved ? <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold text-ink">Saved</span> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {item.tags_json.map((tag) => (
                <span key={tag} className="rounded-full border border-ink/10 px-3 py-1 text-xs text-ink/70">
                  {tag}
                </span>
              ))}
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
              <Link href={item.source_url} className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold" target="_blank">
                Open source
              </Link>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
