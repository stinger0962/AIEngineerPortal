import { notFound } from "next/navigation";

import { LessonCompleteButton } from "@/components/forms/lesson-complete-button";
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
        <article className="prose max-w-none text-sm leading-7 text-ink/80">
          {lesson.content_md.split("\n").map((line, index) => (
            <p key={`${line}-${index}`}>{line}</p>
          ))}
        </article>
        <LessonCompleteButton lessonId={lesson.id} />
      </Panel>
    </div>
  );
}
