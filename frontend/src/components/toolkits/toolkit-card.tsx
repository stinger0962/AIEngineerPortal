"use client";

import Link from "next/link";

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
  const cardClasses = `
    relative rounded-2xl border p-5 transition-all duration-150
    ${comingSoon
      ? "border-dashed border-white/10 opacity-50 cursor-not-allowed"
      : "border-white/10 bg-white/5 hover:border-ember/50 hover:bg-ember/5 cursor-pointer"
    }
  `;

  const inner = (
    <div className={cardClasses}>
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-sm font-bold text-cream mb-1">{name}</h3>
      <p className="text-xs text-cream/50 leading-relaxed mb-4">{description}</p>

      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag.label}
            className={`text-[10px] px-2 py-0.5 rounded font-medium ${
              tag.variant === "ready"
                ? "bg-ember/20 text-ember"
                : tag.variant === "soon"
                ? "bg-white/5 text-cream/30"
                : "bg-white/5 text-cream/40"
            }`}
          >
            {tag.label}
          </span>
        ))}
      </div>
    </div>
  );

  if (href && !comingSoon) {
    return (
      <Link href={href} className="group block">
        {inner}
      </Link>
    );
  }

  return <div className="group">{inner}</div>;
}
