"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { billingApi, type TestOrder } from "@/lib/ziwei/billing";
const labels = { pending: "待确认", paid: "已入账", failed: "失败，未确认入账" };
export function PaidOrderHistory() {
  const [orders, setOrders] = useState<TestOrder[]>([]);
  const [state, setState] = useState<"loading"|"ready"|"error">("loading");
  const request = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++request.current; setState("loading");
    try {
      const value = await billingApi.orders!();
      if (version === request.current) { setOrders(value); setState("ready"); }
    } catch { if (version === request.current) { setOrders([]); setState("error"); } }
  }, []);
  useEffect(() => { void refresh(); return () => { ++request.current; }; }, [refresh]);
  return <section aria-labelledby="recent-orders" className="space-y-4 rounded-2xl border border-ink/15 bg-white/90 p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 id="recent-orders" className="text-lg font-semibold">最近测试订单</h2><button type="button" disabled={state === "loading"} onClick={() => void refresh()} className="min-h-11 rounded-lg border border-violet-300 px-3 text-sm text-violet-900 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-700">刷新订单</button></div>
    {state === "loading" && <p role="status">正在读取订单…</p>}
    {state === "error" && <p role="alert">订单暂不可用，请稍后刷新。不要据此重复付款。</p>}
    {state === "ready" && orders.length === 0 && <p className="text-sm text-ink/75">暂无测试订单。不会仅因浏览此页创建订单。</p>}
    {state === "ready" && orders.length > 0 && <ul className="space-y-3">{orders.map(order => <li key={order.order_id} className="rounded-xl border border-ink/10 p-4 text-sm">
      <div className="flex flex-wrap justify-between gap-2"><span className="font-medium">订单 #{order.order_id}</span><span>{labels[order.status]}</span></div>
      <p className="mt-2">{order.credits} 点 · {(order.amount_cents / 100).toFixed(2)} {order.currency.toUpperCase()} · 测试金额</p>
      <p className="mt-1 text-ink/75">{order.status === "pending" ? "状态未确认，请勿重复购买。" : order.status === "failed" ? "失败状态不是退款凭证；请核对余额后再操作。" : "服务器已确认测试点数入账。"}</p>
    </li>)}</ul>}
    <p className="text-xs leading-relaxed text-ink/70">最多显示最近 10 笔的上次读取状态；付款结果更新后请刷新订单。这里只核对状态，不会发起扣款或退款。</p>
  </section>;
}
