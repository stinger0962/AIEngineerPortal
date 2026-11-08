"use client";

import { paidProduct } from "@/lib/product/config";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckoutStateError, billingApi, canPurchase, paymentReturn, testBillingEnabled, type Balance, type BillingAdapter, type PaymentStatus } from "@/lib/ziwei/billing";

const statusText: Record<PaymentStatus, string> = {
  pending: "测试付款待确认：正在等待服务器入账，请勿重复购买。",
  paid: "测试付款已确认，点数已入账。",
  cancelled: "已返回并取消本次结账操作；这不代表服务器订单已取消。问题仍保留。",
  failed: "测试付款失败，未确认入账。请检查后重试。",
};

export function CreditPanel({ refreshKey, adapter = billingApi }: { refreshKey: number; adapter?: BillingAdapter }) {
  const search = useSearchParams().toString();
  const [balance, setBalance] = useState<Balance | null>(null);
  const [payment, setPayment] = useState<ReturnType<typeof paymentReturn>>(null);
  const [balanceError, setBalanceError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reconciliationOrder, setReconciliationOrder] = useState<string | null>(null);
  const buying = useRef(false);
  const mounted = useRef(false);
  const returnVersion = useRef(0);
  const balanceRequest = useRef(0);
  const statusRequest = useRef(0);
  const purchaseAllowed = canPurchase(balance) && (!paidProduct || testBillingEnabled);
  const refresh = useCallback(async () => {
    const version = ++balanceRequest.current;
    try {
      const value = await adapter.balance();
      if (mounted.current && version === balanceRequest.current) { setBalance(value); setBalanceError(null); }
    } catch { if (mounted.current && version === balanceRequest.current) { setBalance(null); setBalanceError("余额暂不可用，请刷新重试。"); } }
  }, [adapter]);

  useEffect(() => {
    mounted.current = true;
    const restore = () => {
      ++returnVersion.current;
      const returned = paymentReturn(window.location.search);
      setPayment(returned); setPaymentError(null);
      void refresh();
    };
    restore();
    window.addEventListener("pageshow", restore);
    return () => { mounted.current = false; window.removeEventListener("pageshow", restore); };
  }, [search, adapter, refresh]);
  useEffect(() => { void refresh(); }, [refresh, refreshKey]);

  const checkPayment = useCallback(async (orderId: string, preserveCancellation = false) => {
    const version = returnVersion.current;
    const request = ++statusRequest.current;
    try {
      const status = await adapter.status(orderId);
      if (!mounted.current || version !== returnVersion.current || request !== statusRequest.current) return;
      setPayment({ status: status === "pending" && preserveCancellation ? "cancelled" : status, orderId });
      setPaymentError(null);
      if (status === "paid" || status === "failed") adapter.resetCheckout?.(orderId);
      if (status === "paid") await refresh();
    } catch {
      if (mounted.current && version === returnVersion.current && request === statusRequest.current) setPaymentError("付款状态暂无法确认；请稍后刷新，勿重复付款。");
    }
  }, [adapter, refresh]);

  useEffect(() => {
    if (payment?.status === "cancelled" && payment.orderId) {
      // Returning from Checkout does not cancel the provider session. Keep its
      // retry key so another click resumes it, and let server truth win if paid.
      void checkPayment(payment.orderId, true);
    }
  }, [payment?.status, payment?.orderId, checkPayment]);

  useEffect(() => {
    if (payment?.status !== "pending" || !payment.orderId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    const poll = async () => {
      if (cancelled) return;
      await checkPayment(payment.orderId!);
      if (!cancelled && ++attempts < 10) timer = setTimeout(poll, 3000);
    };
    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [payment?.status, payment?.orderId, checkPayment]);

  async function buy(pack: string) {
    if (buying.current || !purchaseAllowed) return;
    ++returnVersion.current;
    buying.current = true;
    setBusy(true);
    setCheckoutError(null);
    try { window.location.assign(await adapter.checkout(pack)); }
    catch (error) {
      if (error instanceof CheckoutStateError) {
        setPayment({ status: error.status, orderId: error.orderId });
        if (error.status === "pending") setReconciliationOrder(error.orderId);
        if (error.status !== "pending") void refresh();
      } else setCheckoutError("无法开启测试收银台。请稍后重试。问题已保留。");
    }
    finally { buying.current = false; setBusy(false); }
  }

  return (
    <section id="ziwei-test-credits" aria-label={paidProduct ? "账号测试点数" : "紫微测试点数"} className="space-y-3 rounded-2xl border border-violet-300 bg-violet-50 p-4 text-sm text-ink">
      <h2 className="font-semibold">{paidProduct ? "账号点数 · 测试模式" : "紫微点数 · Stripe TEST 测试模式"}</h2>
      <p>{paidProduct ? "仅用于测试，请勿使用真实付款资料。点数属于当前登录账号，与浏览器设备无关。" : "仅用于测试，请勿使用真实付款资料。点数属于当前浏览器身份。"}</p>
      <p aria-live="polite">{balance ? `可用点数：${balance.balance}` : balanceError ? "余额暂不可用" : "正在读取余额…"}</p>
      {payment && <p role="status">{statusText[payment.status]}</p>}
      {payment?.status === "pending" && !payment.orderId && <p>缺少订单标识，无法确认付款。请保留测试收据。</p>}
      {payment?.status === "pending" && payment.orderId === reconciliationOrder && <p role="alert">结账已超过安全重试时限，请核对付款状态；不要重复购买。</p>}
      {[balanceError, paymentError, checkoutError].filter(Boolean).map(message => <p key={message} role="alert" className="text-rose-700">{message}</p>)}
      <button type="button" className="underline" onClick={() => { void refresh(); if (payment?.orderId) void checkPayment(payment.orderId, payment.status === "cancelled"); }}>刷新余额与付款状态</button>
      {!purchaseAllowed && <p>测试支付尚未开放，购买已停用。</p>}
      <div className="flex flex-wrap gap-2">
        {(!paidProduct || testBillingEnabled) && balance?.packs.map((pack) => (
          <button key={pack.key} type="button" disabled={!purchaseAllowed || busy || payment?.status === "pending"} onClick={() => void buy(pack.key)} className="rounded-xl border border-violet-300 px-3 py-2 text-left disabled:opacity-50">
            {pack.label} · {pack.credits} 点 · {(pack.amount_cents / 100).toFixed(2)} {(pack.currency ?? balance.currency ?? "CNY").toUpperCase()}{busy ? " · 正在开启…" : " · 测试购买"}
          </button>
        ))}
      </div>
    </section>
  );
}
