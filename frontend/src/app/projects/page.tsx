import Link from "next/link";

import { ProjectEditor } from "@/components/forms/project-editor";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function ProjectsPage() {
  const projects = await portalApi.getProjects();

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Projects" title="Portfolio work should drive the rest of the portal." description="Track the project, the architecture, and the story it creates for interviews." />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel className="space-y-4">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.slug}`} className="block rounded-[24px] bg-cream p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-ink">{project.title}</h3>
                  <p className="mt-2 text-xs uppercase tracking-[0.24em] text-ink/50">
                    {project.category} · {project.status}
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-ink/70">
                  Score {project.portfolio_score}
                </span>
              </div>
              <p className="mt-2 text-sm text-ink/70">{project.summary}</p>
              <div className="mt-4 rounded-2xl bg-white/70 p-4 text-sm text-ink/80">
                <p className="text-xs uppercase tracking-[0.24em] text-rust">Blueprint value</p>
                <p className="mt-2 line-clamp-3">
                  {project.lessons_learned_md.split("\n").find((line) => line.trim() && !line.startsWith("##")) ??
                    "Open the project to see the full architecture and interview story."}
                </p>
              </div>
            </Link>
          ))}
        </Panel>
        <Panel className="space-y-4">
          <SectionHeading eyebrow="Add Project" title="Capture a new build thread" description="Even rough project notes help make the portfolio roadmap visible." />
          <ProjectEditor />
        </Panel>
      </div>
    </div>
  );
}
