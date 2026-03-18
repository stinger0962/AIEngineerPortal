"use client";

import Link from "next/link";
import { startTransition, useDeferredValue, useState } from "react";

import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";
import type { FeedRefreshMeta, JobPosting } from "@/lib/types/portal";

type JobsBoardProps = {
  initialJobs: JobPosting[];
  initialMeta: FeedRefreshMeta;
};

export function JobsBoard({ initialJobs, initialMeta }: JobsBoardProps) {
  const [jobs, setJobs] = useState(initialJobs);
  const [meta, setMeta] = useState(initialMeta);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [savedOnly, setSavedOnly] = useState(false);
  const [minimumFit, setMinimumFit] = useState(0);
  const deferredSearch = useDeferredValue(search);

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      const [refreshed, refreshedMeta] = await Promise.all([portalApi.refreshJobs(), portalApi.getJobsMeta()]);
      startTransition(() => {
        setJobs(refreshed);
        setMeta(refreshedMeta);
      });
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleSave(jobId: number) {
    setActiveJobId(jobId);
    try {
      const saved = await portalApi.saveJob(jobId);
      startTransition(() =>
        setJobs((current) => current.map((job) => (job.id === jobId ? saved : job))),
      );
    } finally {
      setActiveJobId(null);
    }
  }

  async function handleAnalyze(jobId: number) {
    setActiveJobId(jobId);
    try {
      const analysis = await portalApi.analyzeJobFit(jobId);
      startTransition(() =>
        setJobs((current) =>
          current.map((job) =>
            job.id === jobId
              ? { ...job, fit_score: analysis.fit_score, skill_gaps_json: analysis.gaps }
              : job,
          ),
        ),
      );
    } finally {
      setActiveJobId(null);
    }
  }

  const normalizedSearch = deferredSearch.trim().toLowerCase();
  const visibleJobs = jobs.filter((job) => {
    const matchesSaved = !savedOnly || job.is_saved;
    const matchesFit = job.fit_score >= minimumFit;
    const matchesSearch =
      !normalizedSearch ||
      job.title.toLowerCase().includes(normalizedSearch) ||
      job.company_name.toLowerCase().includes(normalizedSearch) ||
      job.summary.toLowerCase().includes(normalizedSearch) ||
      job.tags_json.some((tag) => tag.toLowerCase().includes(normalizedSearch));
    return matchesSaved && matchesFit && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <Panel className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Jobs tracked</p>
              <p className="mt-2 text-3xl font-semibold text-ink">{jobs.length}</p>
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">High fit roles</p>
              <p className="mt-2 text-3xl font-semibold text-ink">
                {jobs.filter((job) => job.fit_score >= 70).length}
              </p>
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Saved roles</p>
              <p className="mt-2 text-3xl font-semibold text-ink">{jobs.filter((job) => job.is_saved).length}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {isRefreshing ? "Refreshing..." : "Refresh jobs"}
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
              placeholder="Search companies, agents, eval..."
              className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-ink/30"
            />
          </label>
          <label className="grid gap-2 text-sm text-ink/70">
            <span className="text-xs uppercase tracking-[0.24em] text-ink/50">Minimum fit</span>
            <select
              value={String(minimumFit)}
              onChange={(event) => setMinimumFit(Number(event.target.value))}
              className="rounded-2xl border border-ink/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-ink/30"
            >
              <option value="0">All roles</option>
              <option value="60">60+</option>
              <option value="70">70+</option>
              <option value="80">80+</option>
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
        {visibleJobs.map((job) => (
          <Panel key={job.id} className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
              <span>{job.company_name}</span>
              <span>{job.location}</span>
              <span>{job.employment_type}</span>
              <span>Fit {job.fit_score}</span>
            </div>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-2xl text-ink">{job.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{job.summary}</p>
              </div>
              {job.is_saved ? (
                <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold text-ink">Saved</span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {job.tags_json.map((tag) => (
                <span key={tag} className="rounded-full border border-ink/10 px-3 py-1 text-xs text-ink/70">
                  {tag}
                </span>
              ))}
            </div>
            <div className="rounded-2xl bg-cream p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Fit read</p>
              <p className="mt-2 text-sm text-ink/70">{job.fit_summary}</p>
              <p className="mt-3 text-sm font-medium text-ink">{job.suggested_action}</p>
            </div>
            {job.skill_gaps_json.length ? (
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Likely gaps</p>
                <p className="mt-2 text-sm text-ink/70">{job.skill_gaps_json.join(" · ")}</p>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => handleAnalyze(job.id)}
                disabled={activeJobId === job.id}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {activeJobId === job.id ? "Analyzing..." : "Analyze fit"}
              </button>
              <button
                type="button"
                onClick={() => handleSave(job.id)}
                disabled={activeJobId === job.id || job.is_saved}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {job.is_saved ? "Saved" : "Save role"}
              </button>
              <Link
                href={job.source_url}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold"
                target="_blank"
              >
                Open posting
              </Link>
            </div>
          </Panel>
        ))}
        {!visibleJobs.length ? (
          <Panel className="text-sm text-ink/70">
            No jobs match the current filters yet. Lower the fit threshold or broaden the search.
          </Panel>
        ) : null}
      </div>
    </div>
  );
}
