import Link from "next/link";
import { notFound } from "next/navigation";

import { ProjectEditor } from "@/components/forms/project-editor";
import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

function curriculumFocus(project: { category: string }) {
  const mapping: Record<string, { path: string; drill: string; interview: string }> = {
    "rag-app": {
      path: "/learn/llm-app-foundations",
      drill: "/practice/python",
      interview: "Use this project to answer RAG trust, retrieval debugging, and evaluation questions with concrete evidence.",
    },
    "agent-system": {
      path: "/learn/ai-agents-and-tools",
      drill: "/practice/python",
      interview: "Use this project to explain when agents add value, how you bound risk, and how you kept workflows auditable.",
    },
    "eval-tooling": {
      path: "/learn/ai-evaluation-and-observability",
      drill: "/practice/python",
      interview: "Use this project to talk about benchmark design, useful metrics, regressions, and iteration discipline.",
    },
  };

  return (
    mapping[project.category] ?? {
      path: "/projects",
      drill: "/practice/python",
      interview: "Tie this project back to system design tradeoffs, delivery decisions, and measurable outcomes.",
    }
  );
}

export default async function ProjectDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const project = await portalApi.getProject(slug);

  if (!project) {
    notFound();
  }

  const focus = curriculumFocus(project);

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Project Detail" title={project.title} description={project.summary} />
      <Panel className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Status</div>
            <p className="mt-2 leading-6">{project.status}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Category</div>
            <p className="mt-2 leading-6">{project.category}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Portfolio score</div>
            <p className="mt-2 leading-6">{project.portfolio_score}</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-mint p-4 text-sm text-ink">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Best next path</div>
            <Link className="mt-2 inline-flex font-semibold underline-offset-4 hover:underline" href={focus.path}>
              {focus.path}
            </Link>
          </div>
          <div className="rounded-2xl bg-mint p-4 text-sm text-ink">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Best next drill</div>
            <Link className="mt-2 inline-flex font-semibold underline-offset-4 hover:underline" href={focus.drill}>
              {focus.drill}
            </Link>
          </div>
          <div className="rounded-2xl bg-mint p-4 text-sm text-ink">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Interview angle</div>
            <p className="mt-2 leading-6">{focus.interview}</p>
          </div>
        </div>
      </Panel>
      <Panel className="space-y-4">
        <SectionHeading eyebrow="Architecture" title="Project blueprint" description="Use this as both build guidance and interview evidence." />
        <LessonMarkdown content={project.architecture_md} />
      </Panel>
      <Panel className="space-y-4">
        <SectionHeading eyebrow="Learning" title="What this project should teach you" description="These notes should get sharper as the project becomes more real." />
        <LessonMarkdown
          content={
            project.lessons_learned_md ||
            "## Next move\nAdd the lessons this project is teaching you so the portal can turn build work into interview proof."
          }
        />
      </Panel>
      <Panel className="space-y-4">
        <SectionHeading eyebrow="Edit" title="Refine the project record" description="Keep architecture notes and lessons learned current." />
        <ProjectEditor initialProject={project} />
      </Panel>
    </div>
  );
}
