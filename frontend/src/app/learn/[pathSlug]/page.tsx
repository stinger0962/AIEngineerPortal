import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, CheckCircle2, Circle, Clock, BookOpen } from "lucide-react";

import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";

export default async function LearningPathPage({ params }: { params: Promise<{ pathSlug: string }> }) {
  const { pathSlug } = await params;
  const path = await portalApi.getPathBySlug(pathSlug);

  if (!path) {
    notFound();
  }

  const completedCount = path.lessons.filter((l: any) => l.is_completed).length;
  const totalCount = path.lessons.length;
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const nextLesson = path.lessons.find((l: any) => !l.is_completed);

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link href="/learn" className="inline-flex items-center gap-2 text-sm text-ink/50 hover:text-ember transition-colors">
        <ArrowLeft size={14} />
        All Learning Paths
      </Link>

      {/* Path hero */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative space-y-4">
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Learning Path</span>
          <h1 className="font-display text-3xl lg:text-4xl leading-tight">{path.title}</h1>
          <p className="text-cream/60 text-[15px] leading-7 max-w-2xl">{path.description}</p>

          {/* Progress bar */}
          <div className="max-w-md pt-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-cream/70">{completedCount} / {totalCount} lessons complete</span>
              <span className="text-sm font-semibold text-ember">{pct}%</span>
            </div>
            <div className="h-3 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-ember to-[#f59e0b] transition-all"
                style={{ width: `${Math.max(pct, 2)}%` }}
              />
            </div>
          </div>

          <div className="flex gap-4 pt-1 text-sm text-cream/50">
            <span className="flex items-center gap-1.5"><Clock size={14} /> {path.estimated_hours}h total</span>
            <span className="flex items-center gap-1.5"><BookOpen size={14} /> {path.level}</span>
          </div>
        </div>
      </div>

      {/* Continue learning CTA */}
      {nextLesson && (
        <Link href={`/learn/lesson/${nextLesson.slug}`}>
          <Panel className="flex items-center justify-between gap-4 border-l-4 border-l-ember hover:shadow-lg transition-shadow cursor-pointer">
            <div>
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-ember">Continue where you left off</span>
              <h3 className="mt-1 font-display text-xl text-ink">{nextLesson.title}</h3>
              <p className="mt-1 text-sm text-ink/60">{nextLesson.summary}</p>
            </div>
            <span className="shrink-0 rounded-full bg-ember px-5 py-2.5 text-sm font-semibold text-white">
              Start lesson
            </span>
          </Panel>
        </Link>
      )}

      {/* Lesson list */}
      <div className="space-y-3">
        {path.lessons.map((lesson: any, index: number) => {
          const isCompleted = lesson.is_completed;
          const isCurrent = nextLesson?.id === lesson.id;

          return (
            <Link key={lesson.id} href={`/learn/lesson/${lesson.slug}`}>
              <div
                className={`flex items-start gap-4 rounded-2xl border p-5 transition-all cursor-pointer ${
                  isCurrent
                    ? "border-ember/30 bg-ember/5 shadow-md"
                    : isCompleted
                    ? "border-mint/40 bg-mint/10 hover:shadow-sm"
                    : "border-ink/10 bg-white hover:border-ink/20 hover:shadow-sm"
                }`}
              >
                {/* Status icon */}
                <div className="shrink-0 mt-0.5">
                  {isCompleted ? (
                    <CheckCircle2 size={22} className="text-pine" />
                  ) : isCurrent ? (
                    <div className="w-[22px] h-[22px] rounded-full border-2 border-ember flex items-center justify-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-ember" />
                    </div>
                  ) : (
                    <Circle size={22} className="text-ink/20" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-ink/40">{index + 1}</span>
                    {isCompleted && <span className="text-[10px] text-pine bg-mint px-2 py-0.5 rounded-full font-medium">Done</span>}
                    {isCurrent && <span className="text-[10px] text-ember bg-ember/10 px-2 py-0.5 rounded-full font-medium">Up next</span>}
                  </div>
                  <h3 className={`mt-1 text-[15px] font-semibold leading-snug ${isCompleted ? "text-ink/60" : "text-ink"}`}>
                    {lesson.title}
                  </h3>
                  <p className="mt-1 text-sm text-ink/50 line-clamp-1">{lesson.summary}</p>
                </div>

                {/* Duration */}
                <span className="shrink-0 text-xs text-ink/40">{lesson.estimated_minutes} min</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
