/** Product-wide factual status, not pricing or a promise of future availability. */
export function PaidPreviewNotice() {
  return <aside aria-label="预览与付费说明" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
    <p className="font-medium">产品预览 · 真实付费尚未开放</p>
    <p className="mt-1 leading-relaxed">此版本不收取真实费用，也不提供充值。账号与体验是否开放，以页面提示为准。</p>
  </aside>;
}
