import Link from "next/link";

import { ProgressChart } from "@/components/dashboard/progress-chart";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function DashboardPage() {
  const [summary, today, recommendations, newsItems, jobs, masteryProfile] = await Promise.all([
    portalApi.getDashboardSummary(),
    portalApi.getDashboardToday(),
    portalApi.getRecommendations(),
    portalApi.getNewsItems(),
    portalApi.getJobs(),
    portalApi.getMasteryProfile(),
  ]);

  const topNews = newsItems[0];
  const topJob = jobs[0];
  const weakestAreas = masteryProfile.slice(0, 3);

  return (
    <div className="space-y-8">
      <Panel className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-4">
          <SectionHeading eyebrow="Today" title={`Welcome back, ${summary.user_name}.`} description={summary.headline} />
          <div className="grid gap-4 md:grid-cols-3">
            {summary.stats.map((stat) => (
              <div key={stat.label} className="rounded-[24px] bg-cream p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-ink/50">{stat.label}</p>
                <p className="mt-3 text-3xl font-semibold text-ink">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-[28px] bg-ink p-6 text-cream">
          <p className="text-xs uppercase tracking-[0.28em] text-cream/60">Next best step</p>
          <h3 className="mt-3 font-display text-3xl">{summary.next_lesson?.title}</h3>
          <p className="mt-3 text-sm text-cream/80">{summary.next_lesson?.summary}</p>
          <Link
            href={`/learn/lesson/${summary.next_lesson?.slug}`}
            className="mt-6 inline-flex rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white"
          >
            Open lesson
          </Link>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel>
          <SectionHeading
            eyebrow="Progress"
            title="Momentum over the last month"
            description="Track learning depth and practice volume together."
          />
          <ProgressChart />
        </Panel>
        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Daily plan"
            title="What to focus on next"
            description="Use one concrete action per stream to keep the transition manageable."
          />
          <div className="space-y-3">
            {today.focus.map((item) => (
              <div key={item} className="rounded-2xl bg-mint p-4 text-sm text-ink">
                {item}
              </div>
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {today.highlights.map((item) => (
              <div key={item} className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
                {item}
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {summary.adaptive_focus ? (
        <Panel className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <SectionHeading
              eyebrow="Adaptive focus"
              title={summary.adaptive_focus.title}
              description="Phase 5 starts by identifying the weakest area in your current system and turning it into a focused sprint."
            />
            <div className="rounded-[24px] bg-cream p-5">
              <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
                <span>{summary.adaptive_focus.area_title}</span>
                <span>{summary.adaptive_focus.target_kind}</span>
                <span>Mastery {summary.adaptive_focus.mastery_score}/100</span>
              </div>
              <p className="mt-3 text-sm leading-7 text-ink/75">{summary.adaptive_focus.reason}</p>
              <Link
                href={summary.adaptive_focus.action_path}
                className="mt-5 inline-flex rounded-full bg-ink px-5 py-3 text-sm font-semibold text-cream"
              >
                {summary.adaptive_focus.action_label}
              </Link>
            </div>
          </div>
          <div className="space-y-4">
            <SectionHeading
              eyebrow="Mastery"
              title="Weakest areas right now"
              description="This view blends lesson progress, drill reps, interview reps, and signal demand."
            />
            {weakestAreas.map((area) => (
              <div key={area.area_slug} className="rounded-2xl bg-mint p-4 text-sm text-ink">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold">{area.area_title}</p>
                  <span className="rounded-full bg-white px-3 py-1 text-xs uppercase tracking-[0.2em] text-ink/60">
                    {area.status}
                  </span>
                </div>
                <p className="mt-2 text-ink/75">{area.gap}</p>
                <p className="mt-2 text-xs text-ink/60">{area.evidence}</p>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-4">
        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Practice"
            title={summary.recommended_exercise?.title ?? "Recommended practice"}
            description="Keep the fundamentals active while you build."
          />
          <p className="text-sm text-ink/70">
            Category: {summary.recommended_exercise?.category} | Difficulty: {summary.recommended_exercise?.difficulty}
          </p>
          <Link href="/practice/python" className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold">
            Open practice hub
          </Link>
        </Panel>

        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Projects"
            title="Active portfolio work"
            description="Keep one or two projects in motion and let them drive learning."
          />
          {summary.active_projects.map((project) => (
            <div key={project.id} className="rounded-2xl bg-white p-4">
              <p className="font-semibold text-ink">{project.title}</p>
              <p className="text-sm text-ink/70">{project.status} | Portfolio score {project.portfolio_score}</p>
            </div>
          ))}
        </Panel>

        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Recommendations"
            title="Actionable guidance"
            description="Phase 2 now blends internal priorities with external signals."
          />
          {recommendations.map((recommendation) => (
            <div key={recommendation.title} className="rounded-2xl bg-cream p-4">
              <p className="font-semibold text-ink">{recommendation.title}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.24em] text-ink/50">{recommendation.source_kind}</p>
              <p className="mt-2 text-sm text-ink/70">{recommendation.reason}</p>
            </div>
          ))}
        </Panel>

        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Signals"
            title={topNews?.title ?? "Top external signal"}
            description="Keep market and tooling movement close to the daily workflow."
          />
          {topNews ? (
            <>
              <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/55">
                <span>{topNews.source_name}</span>
                <span>Signal {topNews.signal_score}</span>
                {topNews.is_saved ? <span className="rounded-full bg-ink px-2 py-1 text-[10px] text-cream">Saved</span> : null}
              </div>
              <p className="text-sm text-ink/70">{topNews.summary}</p>
              <p className="text-sm text-ink/70">{topNews.why_it_matters}</p>
              <Link href="/news" className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold">
                Open news feed
              </Link>
            </>
          ) : null}
          {topJob ? (
            <div className="rounded-2xl bg-cream p-4">
              <p className="font-semibold text-ink">{topJob.title}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-ink/70">
                <span>{topJob.company_name} | Fit {topJob.fit_score}</span>
                {topJob.is_saved ? <span className="rounded-full bg-ink px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-cream">Saved</span> : null}
              </div>
              <p className="mt-2 text-sm text-ink/70">{topJob.fit_summary}</p>
              <Link href="/jobs" className="mt-3 inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold">
                Open jobs
              </Link>
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
