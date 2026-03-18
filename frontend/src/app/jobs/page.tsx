import { JobsBoard } from "@/components/intelligence/jobs-board";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function JobsPage() {
  const [jobs, meta] = await Promise.all([portalApi.getJobs(), portalApi.getJobsMeta()]);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Jobs"
        title="Opportunity tracking with fit scoring"
        description="Keep relevant AI engineer roles in view, inspect likely strengths and gaps, and let market signals sharpen what you build next."
      />
      <JobsBoard initialJobs={jobs} initialMeta={meta} />
    </div>
  );
}
