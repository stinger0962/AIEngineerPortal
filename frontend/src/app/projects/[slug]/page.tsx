import { notFound } from "next/navigation";

import { ProjectEditor } from "@/components/forms/project-editor";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function ProjectDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const project = await portalApi.getProject(slug);

  if (!project) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Project Detail" title={project.title} description={project.summary} />
      <Panel className="space-y-4">
        <p className="text-sm text-ink/70">
          {project.category} · {project.status} · score {project.portfolio_score}
        </p>
        <p className="text-sm leading-7 text-ink/80">{project.architecture_md}</p>
      </Panel>
      <Panel className="space-y-4">
        <SectionHeading eyebrow="Edit" title="Refine the project record" description="Keep architecture notes and lessons learned current." />
        <ProjectEditor initialProject={project} />
      </Panel>
    </div>
  );
}
