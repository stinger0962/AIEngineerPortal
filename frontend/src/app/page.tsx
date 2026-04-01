import Link from "next/link";
import { BookOpen, Brain, Code2, MessageSquare, Target, TrendingUp, Zap } from "lucide-react";

import { ProgressChart } from "@/components/dashboard/progress-chart";
import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";

export default async function DashboardPage() {
  const [summary, today, masteryProfile, streak] = await Promise.all([
    portalApi.getDashboardSummary(),
    portalApi.getDashboardToday(),
    portalApi.getMasteryProfile(),
    portalApi.getStreakSummary(),
  ]);

  const weakestAreas = masteryProfile.slice(0, 3);
  const strongestAreas = masteryProfile.slice(-2);

  return (
    <div className="space-y-6">
      {/* Hero — greeting + next action */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-8 text-cream">
        <div className="absolute top-0 right-0 w-80 h-80 bg-ember/8 rounded-full blur-3xl -translate-y-1/3 translate-x-1/4" />
        <div className="relative grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="space-y-4">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Dashboard</span>
            <h1 className="font-display text-3xl lg:text-4xl leading-tight">
              Welcome back, {summary.user_name}.
            </h1>
            <p className="text-cream/60 text-[15px] leading-7 max-w-xl">{summary.headline}</p>

            {/* Quick stats */}
            <div className="flex flex-wrap gap-4 pt-2">
              {summary.stats.map((stat) => (
                <div key={stat.label} className="rounded-2xl bg-white/10 px-5 py-3 text-center min-w-[100px]">
                  <p className="text-2xl font-bold text-cream">{stat.value}</p>
                  <p className="text-[10px] uppercase tracking-wide text-cream/50 mt-1">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Next best step */}
          {summary.next_lesson && (
            <div className="rounded-2xl bg-white/10 backdrop-blur p-6 space-y-3 border border-white/10">
              <div className="flex items-center gap-2">
                <Zap size={14} className="text-ember" />
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-ember">Continue learning</span>
              </div>
              <h3 className="font-display text-xl text-cream">{summary.next_lesson.title}</h3>
              <p className="text-sm text-cream/60 line-clamp-2">{summary.next_lesson.summary}</p>
              <Link
                href={`/learn/lesson/${summary.next_lesson.slug}`}
                className="inline-flex rounded-full bg-ember px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#e06f00] transition-colors"
              >
                Open lesson
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Streak bar */}
      <Panel className="flex items-center justify-between gap-6 flex-wrap">
        {/* Current streak */}
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold ${streak.is_active_today ? "bg-ember text-white" : "bg-ink/10 text-ink/40"}`}>
            {streak.current_streak}
          </div>
          <div>
            <p className="text-sm font-semibold text-ink">Day streak</p>
            <p className="text-xs text-ink/50">Best: {streak.longest_streak} days</p>
          </div>
        </div>

        {/* Week dots */}
        <div className="flex items-center gap-2">
          {["M", "T", "W", "T", "F", "S", "S"].map((day, i) => (
            <div key={i} className="text-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                streak.week_activity[i] ? "bg-pine text-white" : "bg-ink/5 text-ink/30"
              }`}>
                {day}
              </div>
            </div>
          ))}
        </div>

        {/* Today's stats */}
        <div className="flex gap-4">
          <div className="text-center">
            <p className="text-xl font-bold text-ink">{streak.today_exercises}</p>
            <p className="text-[10px] uppercase tracking-wide text-ink/40">Exercises</p>
          </div>
          <div className="text-center">
            <p className="text-xl font-bold text-ink">{streak.today_reviews}</p>
            <p className="text-[10px] uppercase tracking-wide text-ink/40">Reviews</p>
          </div>
        </div>

        {/* CTA if not active today */}
        {!streak.is_active_today && (
          <Link href="/practice/python" className="rounded-full bg-ember px-4 py-2 text-sm font-semibold text-white hover:bg-[#e06f00] transition-colors">
            Start today&apos;s practice
          </Link>
        )}
      </Panel>

      {/* Quick actions row */}
      <div className="grid gap-4 md:grid-cols-5">
        {[
          { href: "/learn", icon: BookOpen, label: "Learn", desc: "Continue your path", color: "text-pine" },
          { href: "/practice/python", icon: Code2, label: "Practice", desc: "Hands-on drills", color: "text-ember" },
          { href: "/review", icon: Brain, label: "Review", desc: "Spaced repetition", color: "text-[#8b5cf6]" },
          { href: "/interview", icon: Target, label: "Interview", desc: "AI coaching", color: "text-[#f43f5e]" },
          { href: "/copilot", icon: MessageSquare, label: "Copilot", desc: "Ask anything", color: "text-[#0ea5e9]" },
        ].map(({ href, icon: Icon, label, desc, color }) => (
          <Link key={href} href={href}>
            <Panel className="flex items-center gap-3 hover:shadow-lg transition-shadow cursor-pointer h-full">
              <Icon size={20} className={color} />
              <div>
                <p className="text-sm font-semibold text-ink">{label}</p>
                <p className="text-xs text-ink/50">{desc}</p>
              </div>
            </Panel>
          </Link>
        ))}
      </div>

      {/* Two-column: Progress + Daily focus */}
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Panel>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} className="text-ember" />
            <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Progress</h2>
          </div>
          <ProgressChart />
        </Panel>

        <Panel className="space-y-4">
          <div className="flex items-center gap-2">
            <Target size={16} className="text-pine" />
            <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-pine">Today&apos;s Focus</h2>
          </div>
          <div className="space-y-3">
            {today.focus.map((item, i) => (
              <div key={item} className="flex gap-3 text-sm text-ink/80">
                <span className="shrink-0 w-6 h-6 rounded-full bg-mint flex items-center justify-center text-xs font-bold text-pine">{i + 1}</span>
                <span className="leading-6">{item}</span>
              </div>
            ))}
          </div>
          {today.highlights?.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-ink/5">
              {today.highlights.slice(0, 3).map((item) => (
                <p key={item} className="text-xs text-ink/50 leading-5">{item}</p>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Mastery overview */}
      {summary.adaptive_focus && (
        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          {/* Weakest areas */}
          <Panel className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Weakest Areas</h2>
              <Link href="/learn" className="text-xs text-ember hover:text-ink transition-colors">View all paths →</Link>
            </div>
            {weakestAreas.map((area) => (
              <div key={area.area_slug} className="flex items-center gap-4">
                <div className="w-full">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-ink">{area.area_title}</p>
                    <span className="text-xs text-ink/50">{area.mastery_score}/100</span>
                  </div>
                  <div className="h-2 rounded-full bg-ink/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-ember to-[#f59e0b] transition-all"
                      style={{ width: `${Math.max(area.mastery_score, 3)}%` }}
                    />
                  </div>
                  <p className="text-xs text-ink/40 mt-1">{area.gap}</p>
                </div>
              </div>
            ))}

            {/* Adaptive focus action */}
            <div className="rounded-xl bg-ember/5 border border-ember/10 p-4">
              <p className="text-xs font-semibold text-ember uppercase tracking-wide">Recommended Focus</p>
              <p className="text-sm text-ink/70 mt-1">{summary.adaptive_focus.reason}</p>
              <Link
                href={summary.adaptive_focus.action_path}
                className="mt-3 inline-flex rounded-full bg-ember px-4 py-2 text-xs font-semibold text-white hover:bg-[#e06f00] transition-colors"
              >
                {summary.adaptive_focus.action_label}
              </Link>
            </div>
          </Panel>

          {/* Recommended exercise + practice stats */}
          <Panel className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-pine">Recommended Practice</h2>

            {summary.recommended_exercise && (
              <div className="rounded-xl bg-mint/30 border border-mint p-4 space-y-2">
                <h3 className="text-sm font-semibold text-ink">{summary.recommended_exercise.title}</h3>
                <div className="flex gap-2">
                  <span className="text-[10px] bg-sand px-2 py-0.5 rounded-full text-ink/60 uppercase tracking-wide">{summary.recommended_exercise.category}</span>
                  <span className="text-[10px] bg-sand px-2 py-0.5 rounded-full text-ink/60 uppercase tracking-wide">{summary.recommended_exercise.difficulty}</span>
                </div>
                <Link
                  href="/practice/python"
                  className="inline-flex rounded-full bg-pine px-4 py-2 text-xs font-semibold text-white hover:bg-ink transition-colors"
                >
                  Start practicing
                </Link>
              </div>
            )}

            {/* Strongest areas */}
            <div className="pt-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink/40 mb-3">Strongest Areas</p>
              {strongestAreas.map((area) => (
                <div key={area.area_slug} className="flex items-center gap-4 mb-3">
                  <div className="w-full">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium text-ink">{area.area_title}</p>
                      <span className="text-xs text-pine">{area.mastery_score}/100</span>
                    </div>
                    <div className="h-2 rounded-full bg-ink/10 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-pine to-mint transition-all"
                        style={{ width: `${Math.max(area.mastery_score, 3)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
