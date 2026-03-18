import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function JobsPage() {
  const jobs = await portalApi.getJobs();

  return (
    <div className="space-y-6">
      <Panel className="space-y-4">
        <SectionHeading
          eyebrow="Jobs"
          title="Opportunity tracking with fit scoring"
          description="Use Phase 2 to keep relevant AI engineer roles in view, inspect likely strengths and gaps, and let market signals sharpen what you build next."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Jobs tracked</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{jobs.length}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">High fit roles</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{jobs.filter((job) => job.fit_score >= 70).length}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Saved roles</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{jobs.filter((job) => job.is_saved).length}</p>
          </div>
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
              {job.is_saved ? <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold text-ink">Saved</span> : null}
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
            <Link href={job.source_url} className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold" target="_blank">
              Open posting
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
