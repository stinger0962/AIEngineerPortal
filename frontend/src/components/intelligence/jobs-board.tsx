"use client";

import Link from "next/link";
import { startTransition, useState } from "react";

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
      </Panel>

      <div className="grid gap-4">
        {jobs.map((job) => (
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
      </div>
    </div>
  );
}
