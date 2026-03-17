export function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">{eyebrow}</p>
      <h2 className="font-display text-3xl text-ink">{title}</h2>
      <p className="max-w-2xl text-sm text-ink/70">{description}</p>
    </div>
  );
}
