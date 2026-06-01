import Link from "next/link";
import { cn } from "@/lib/utils";

interface Tag {
  label: string;
  variant?: "default" | "ready" | "soon";
}

interface ToolkitCardProps {
  icon: string;
  name: string;
  description: string;
  tags?: Tag[];
  href?: string;
  comingSoon?: boolean;
}

export function ToolkitCard({
  icon,
  name,
  description,
  tags = [],
  href,
  comingSoon = false,
}: ToolkitCardProps) {
  const card = (
    <div
      className={cn(
        "group relative rounded-[28px] border p-6 transition-all duration-150 h-full flex flex-col",
        comingSoon
          ? "border-dashed border-ink/20 bg-white/40 opacity-60 cursor-not-allowed"
          : "border-ink/10 bg-white/85 shadow-panel hover:border-ember/40 hover:shadow-lg cursor-pointer"
      )}
    >
      {/* Icon */}
      <div className="text-4xl mb-4">{icon}</div>

      {/* Name */}
      <h3 className="font-display text-lg font-semibold text-ink mb-1">{name}</h3>

      {/* Description */}
      <p className="text-sm text-ink/60 leading-relaxed flex-1 mb-4">{description}</p>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag.label}
              className={cn(
                "text-[11px] px-2.5 py-0.5 rounded-full font-medium",
                tag.variant === "ready"
                  ? "bg-ember/15 text-ember"
                  : tag.variant === "soon"
                  ? "bg-ink/8 text-ink/40"
                  : "bg-ink/8 text-ink/50"
              )}
            >
              {tag.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  if (href && !comingSoon) {
    return (
      <Link href={href} className="block h-full">
        {card}
      </Link>
    );
  }

  return card;
}
