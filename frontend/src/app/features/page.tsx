import Link from "next/link";
import { notFound } from "next/navigation";
import { paidFeatures, paidProduct } from "@/lib/product/config";
import { PaidPreviewNotice } from "@/components/product/preview-notice";

export default function FeaturesPage() {
  if (!paidProduct) notFound();
  return (
    <section className="mx-auto max-w-5xl space-y-8 py-4 sm:py-8">
      <div>
        <p className="text-sm tracking-[0.3em] text-violet-800">方寸 · 玄</p>
        <h1 className="mt-3 text-3xl font-semibold">探索功能</h1>
        <p className="mt-3 max-w-2xl leading-relaxed text-ink/80">一张星盘，看见长线的自己；一支灵签，梳理眼前的心事。选一扇适合此刻的门。</p>
      </div>
      <PaidPreviewNotice />
      <div className="grid gap-5 sm:grid-cols-2">
        {paidFeatures.map((feature) => (
          <article key={feature.id} aria-labelledby={`feature-${feature.id}`} className="flex flex-col rounded-2xl border border-ink/15 bg-white/90 p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <span aria-hidden="true" className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-4xl" style={{ color: feature.accent }}>{feature.character}</span>
              <div><p className="text-xs uppercase tracking-widest text-ink/70">{feature.english}</p><h2 id={`feature-${feature.id}`} className="mt-1 text-xl font-semibold">{feature.label}</h2></div>
            </div>
            <p className="mt-5 leading-relaxed text-ink/90">{feature.purpose}</p>
            <p className="mt-3 text-sm leading-relaxed text-ink/75">{feature.description}</p>
            <div className="my-5 rounded-lg bg-stone-50 p-3 text-sm leading-relaxed"><p className="font-medium">开始前</p><p className="mt-1 text-ink/80">{feature.preparation}</p></div>
            <Link href={feature.href} className="mt-auto inline-flex min-h-11 items-center justify-center rounded-xl border border-violet-300 bg-violet-50 px-4 py-3 font-medium text-violet-900 hover:bg-violet-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet-700">了解{feature.label}<span aria-hidden="true" className="ml-2">→</span></Link>
          </article>
        ))}
      </div>
      <section aria-labelledby="how-to-start" className="rounded-2xl border border-ink/10 bg-white/60 p-6">
        <h2 id="how-to-start" className="text-xl font-medium">从哪里开始？</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-5 text-sm leading-relaxed text-ink/85">
          <li>先选体验。探索页无需登录，可以随时返回比较。</li>
          <li>账号开放后，用邮箱验证码登录。紫微档案、灵签记录和点数使用同一个账号。</li>
          <li>再进入对应功能。未开放时会说明状态，不会要求你付款。</li>
        </ol>
        <Link href="/account" className="mt-5 inline-flex min-h-11 items-center rounded-lg px-1 text-sm font-medium text-violet-900 underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-700">查看账号状态</Link>
      </section>
      <p className="text-sm leading-relaxed text-ink/75">内容仅供文化探索与娱乐，不构成医疗、法律、财务等专业建议。更多功能会沿用同一个入口与账号，不必重新寻找。</p>
    </section>
  );
}
