import Link from "next/link";
import { notFound } from "next/navigation";
import { BookOpen, CheckCircle2, Clock, Tag, ArrowLeft } from "lucide-react";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { LessonCompleteButton } from "@/components/forms/lesson-complete-button";
import { DeepDiveSection } from "@/components/learning/deep-dive-section";
import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";

export default async function LessonPage({ params }: { params: Promise<{ lessonSlug: string }> }) {
  const { lessonSlug } = await params;
  const lesson = await portalApi.getLesson(lessonSlug);

  if (!lesson) {
    notFound();
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/learn"
        className="inline-flex items-center gap-2 text-sm text-ink/50 hover:text-ember transition-colors"
      >
        <ArrowLeft size={14} />
        Back to Learning Paths
      </Link>

      {/* Hero header */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Lesson</span>
            {lesson.is_completed && (
              <span className="inline-flex items-center gap-1 rounded-full bg-mint/20 px-3 py-1 text-xs font-medium text-mint">
                <CheckCircle2 size={12} />
                Completed
              </span>
            )}
          </div>
          <h1 className="font-display text-3xl lg:text-4xl leading-tight">{lesson.title}</h1>
          <p className="text-cream/70 text-[15px] leading-7 max-w-2xl">{lesson.summary}</p>

          {/* Meta row */}
          <div className="flex flex-wrap gap-4 pt-2">
            <div className="flex items-center gap-2 text-sm text-cream/60">
              <Clock size={14} />
              <span>{lesson.estimated_minutes} min</span>
            </div>
            {lesson.tags_json?.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-cream/60">
                <Tag size={14} />
                <div className="flex gap-1.5">
                  {lesson.tags_json.map((tag: string) => (
                    <span key={tag} className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs text-cream/70">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Prerequisites */}
      {lesson.prerequisites_json?.length > 0 && (
        <div className="flex items-start gap-3 rounded-2xl border border-sand bg-sand/30 px-5 py-4">
          <BookOpen size={18} className="text-pine mt-0.5 shrink-0" />
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-pine">Prerequisites</span>
            <div className="mt-1 flex flex-wrap gap-2">
              {lesson.prerequisites_json.map((prereq: string) => (
                <Link
                  key={prereq}
                  href={`/learn/lesson/${prereq}`}
                  className="text-sm text-ember hover:text-ink underline underline-offset-2 transition-colors"
                >
                  {prereq.replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Lesson content */}
      <Panel className="space-y-0">
        <article>
          <LessonMarkdown content={lesson.content_md} />
        </article>
      </Panel>

      {/* Actions */}
      <div className="flex flex-col gap-4">
        <LessonCompleteButton lessonId={lesson.id} />
        <Panel>
          <DeepDiveSection lessonId={lesson.id} />
        </Panel>
      </div>
    </div>
  );
}
