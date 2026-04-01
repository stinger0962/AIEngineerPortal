"use client";

import { useState, useEffect } from "react";
import { Search, ExternalLink, MapPin, Building2, Tag } from "lucide-react";
import { portalApi } from "@/lib/api/portal";
import { LiveJob } from "@/lib/types/portal";
import { Panel } from "@/components/ui/panel";

export default function LiveJobsPage() {
  const [jobs, setJobs] = useState<LiveJob[]>([]);
  const [query, setQuery] = useState("ai engineer");
  const [loading, setLoading] = useState(true);

  async function searchJobs(q: string) {
    setLoading(true);
    const result = await portalApi.searchLiveJobs(q);
    setJobs(result.jobs);
    setLoading(false);
  }

  useEffect(() => { searchJobs(query); }, []);

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-5 lg:p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative space-y-3">
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Job Search</span>
          <h1 className="font-display text-3xl lg:text-4xl leading-tight">Real AI Engineer jobs, live.</h1>
          <p className="text-cream/60 text-[15px] max-w-2xl">Powered by Himalayas.app — real remote job postings updated daily. No mock data.</p>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink/30" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchJobs(query)}
            placeholder="Search jobs... (e.g. ai engineer, ml ops, rag developer)"
            className="w-full rounded-xl border border-ink/10 bg-white pl-10 pr-4 py-3 text-sm text-ink placeholder:text-ink/40 focus:outline-none focus:ring-2 focus:ring-ember/30 focus:border-ember"
          />
        </div>
        <button
          onClick={() => searchJobs(query)}
          className="rounded-xl bg-ember px-6 py-3 text-sm font-semibold text-white hover:bg-[#e06f00] transition-colors"
        >
          Search
        </button>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-12 text-ink/40">Searching jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-ink/40">No jobs found. Try a different search term.</div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-ink/40">{jobs.length} jobs found</p>
          {jobs.map((job, i) => (
            <a key={i} href={job.url} target="_blank" rel="noopener noreferrer">
              <Panel className="hover:shadow-lg transition-shadow cursor-pointer space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h3 className="text-[15px] font-semibold text-ink flex items-center gap-2">
                      {job.title}
                      <ExternalLink size={12} className="text-ink/30" />
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-ink/50">
                      <span className="flex items-center gap-1"><Building2 size={12} /> {job.company_name}</span>
                      <span className="flex items-center gap-1"><MapPin size={12} /> {job.location}</span>
                      {job.salary_range && job.salary_range.trim() !== "-" && (
                        <span className="text-pine font-medium">{job.salary_range}</span>
                      )}
                    </div>
                  </div>
                  {job.seniority && (
                    <span className="shrink-0 text-[10px] uppercase tracking-wide bg-sand px-2 py-0.5 rounded-full text-ink/60">
                      {job.seniority}
                    </span>
                  )}
                </div>
                {job.description_snippet && (
                  <p className="text-sm text-ink/50 line-clamp-2">{job.description_snippet.replace(/<[^>]*>/g, '')}</p>
                )}
                {job.tags?.length > 0 && (
                  <div className="flex gap-1.5 flex-wrap">
                    {job.tags.slice(0, 5).map((tag) => (
                      <span key={tag} className="text-[10px] text-ink/40 bg-ink/5 px-2 py-0.5 rounded-full">{tag}</span>
                    ))}
                  </div>
                )}
              </Panel>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
