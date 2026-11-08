import { Suspense } from "react";
import { notFound } from "next/navigation";
import { paidProduct } from "@/lib/product/config";
import { CreditPanel } from "@/components/ziwei/billing/credit-panel";
import { PaidOrderHistory } from "@/components/product/order-history";
import { PaidPreviewNotice } from "@/components/product/preview-notice";

export default function CreditsPage() {
  if (!paidProduct) notFound();
  return <section className="mx-auto max-w-3xl space-y-6">
    <div><h1 className="text-2xl font-semibold">点数与订单</h1><p className="mt-2 text-sm leading-relaxed text-ink/80">在这里核对当前账号的测试点数与最近订单。页面返回提示不等于付款确认，一切以服务器记录为准。</p></div>
    <PaidPreviewNotice />
    <Suspense fallback={<p role="status">正在读取点数…</p>}><CreditPanel refreshKey={0} /></Suspense>
    <PaidOrderHistory />
    <aside className="rounded-xl border border-ink/15 bg-white/70 p-4 text-sm leading-relaxed text-ink/85" aria-label="失败与返还说明">
      <h2 className="font-medium">遇到失败或点数不符？</h2>
      <p className="mt-2">不要重复付款或提交同一个解读。先刷新余额和订单状态，并保留订单编号。关闭收银台或返回页面，不代表订单已取消或退款。</p>
      <p className="mt-2">解读失败后的点数返还请以刷新后的余额为准。本预览不收取真实费用，也不提供真实付款退款操作。</p>
    </aside>
  </section>;
}
