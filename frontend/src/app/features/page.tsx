import Link from "next/link";
import { notFound } from "next/navigation";
import { paidFeatures, paidProduct } from "@/lib/product/config";

export default function FeaturesPage() {
  if (!paidProduct) notFound();
  return (
    <section className="mx-auto max-w-5xl space-y-8 py-8">
      <div>
        <p className="text-sm tracking-[0.3em] text-violet-700">方寸 · 玄</p>
        <h1 className="mt-3 text-3xl font-semibold">探索功能</h1>
        <p className="mt-3 text-ink/60">从一张星盘、一支灵签开始。更多体验将在这里相遇。</p>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        {paidFeatures.map((feature) => (
          <Link key={feature.id} href={feature.href} className="rounded-2xl border border-ink/10 bg-white/70 p-6 transition hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-600">
            <span className="text-4xl" style={{ color: feature.accent }}>{feature.character}</span>
            <h2 className="mt-4 text-xl font-medium">{feature.label}</h2>
            <p className="mt-2 text-sm text-ink/60">{feature.description}</p>
            <p className="mt-6 text-sm text-violet-700">进入体验 →</p>
          </Link>
        ))}
      </div>
      <p className="text-sm text-ink/60">预览阶段，真实付费尚未开放。内容仅供文化探索与娱乐，不构成专业建议。</p>
    </section>
  );
}
