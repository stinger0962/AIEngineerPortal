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
              <div className="flex items-center justify-between gap-4">
                <h3 className="text-lg font-semibold text-ink">{project.title}</h3>
                <span className="text-sm text-ink/60">{project.portfolio_score}</span>
              </div>
              <p className="mt-2 text-sm text-ink/70">{project.summary}</p>
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
