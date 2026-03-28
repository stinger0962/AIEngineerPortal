import { notFound } from "next/navigation";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { LessonCompleteButton } from "@/components/forms/lesson-complete-button";
import { DeepDiveSection } from "@/components/learning/deep-dive-section";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function LessonPage({ params }: { params: Promise<{ lessonSlug: string }> }) {
  const { lessonSlug } = await params;
  const lesson = await portalApi.getLesson(lessonSlug);

  if (!lesson) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Lesson" title={lesson.title} description={lesson.summary} />
      <Panel className="space-y-6">
        <div className="flex flex-wrap items-center gap-3 text-sm text-ink/70">
          <span>{lesson.estimated_minutes} minutes</span>
          <span>{lesson.is_completed ? "Completed" : "In progress"}</span>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/75">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Lesson focus</div>
            <p className="mt-2 leading-6">{lesson.summary}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/75">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Prerequisites</div>
            <p className="mt-2 leading-6">
              {lesson.prerequisites_json.length > 0 ? lesson.prerequisites_json.join(", ") : "None. This is an entry lesson."}
            </p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/75">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Tags</div>
            <p className="mt-2 leading-6">{lesson.tags_json.join(" · ")}</p>
          </div>
        </div>
        <article className="space-y-4">
          <LessonMarkdown content={lesson.content_md} />
        </article>
        <LessonCompleteButton lessonId={lesson.id} />
        <DeepDiveSection lessonId={lesson.id} />
      </Panel>
    </div>
  );
}
