import { cn } from "@/lib/utils";

export function Panel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-[28px] border border-ink/10 bg-white/85 p-6 shadow-panel backdrop-blur", className)}>
      {children}
    </section>
  );
}
