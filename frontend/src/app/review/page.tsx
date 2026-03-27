import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";
import { ReviewSession } from "@/components/review/review-session";

export default async function ReviewPage() {
  const cards = await portalApi.getMemoryCards();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Memory Review"
        title="Flip, recall, reinforce."
        description="Spaced repetition cards drawn from your lessons, exercises, and interview prep. Rate your confidence to surface weak spots."
      />
      <ReviewSession cards={cards} />
    </div>
  );
}
