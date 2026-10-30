import { API_BASE } from "@/lib/api";
import { retryKeys } from "./retry-keys";
import { getDeviceId } from "@/lib/deviceId";

// Deliberate opt-in; never enables the server's paywall.
export const testBillingEnabled = process.env.NEXT_PUBLIC_ZIWEI_TEST_BILLING === "true";
export type CreditPack = { key: string; label: string; credits: number; amount_cents: number; currency?: string };
export type Balance = { balance: number; paid_enabled: boolean; require_credits: boolean; mode?: string; currency?: string; packs: CreditPack[] };
export type PaymentStatus = "pending" | "paid" | "cancelled" | "failed";
export class CheckoutStateError extends Error {
  constructor(public code: string, public orderId: string, public status: PaymentStatus) {
    super(code);
  }
}
export interface BillingAdapter {
  balance(): Promise<Balance>;
  checkout(pack: string): Promise<string>;
  status(orderId: string): Promise<PaymentStatus>;
  resetCheckout?(orderId: string): void;
}

export function paymentReturn(search: string): { status: PaymentStatus; orderId?: string } | null {
  const params = new URLSearchParams(search);
  if (params.get("canceled") === "1" || params.get("cancelled") === "1") return { status: "cancelled", orderId: params.get("order_id") || undefined };
  if (params.get("paid") === "1") return { status: "pending", orderId: params.get("order_id") || undefined };
  return null;
}

export function canPurchase(balance: Balance | null): boolean {
  return balance?.mode === "test" && balance.paid_enabled;
}

export function testCheckoutUrl(value: string): string {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.hostname !== "checkout.stripe.com" || !url.pathname.startsWith("/c/pay/cs_test_") || url.username || url.password || url.port) {
    throw new Error("Only Stripe test Checkout is allowed");
  }
  return url.href;
}

// Backend contract reconciliation belongs here; components also accept an injected mock.
export function createBillingAdapter(base: string, deviceId: () => string, transport: typeof fetch = fetch): BillingAdapter {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const device = deviceId();
    if (!device) throw new Error("Device identity unavailable");
    const response = await transport(`${base}/billing${path}`, {
      ...init, cache: "no-store",
      headers: { "Content-Type": "application/json", "X-Device-Id": device, ...init?.headers },
    });
    if (!response.ok) {
      if (response.status === 409) {
        const detail = (await response.json()).detail;
        if (detail?.mode === "test" && /^[0-9]+$/.test(String(detail.order_id)) &&
            ((detail.code === "checkout_paid" && detail.status === "paid") ||
             (detail.code === "checkout_failed" && detail.status === "failed") ||
             (detail.code === "checkout_reconciliation_required" && detail.status === "pending"))) {
          throw new CheckoutStateError(detail.code, String(detail.order_id), detail.status);
        }
      }
      throw new Error(`Billing unavailable (${response.status})`);
    }
    return response.json() as Promise<T>;
  }
  return {
    resetCheckout: (orderId) => retryKeys.complete(`checkout:${deviceId()}`, orderId),
    balance: () => request<Balance>("/balance"),
    checkout: async (pack) => {
      // Recheck server mode immediately before creating a session.
      if (!canPurchase(await request<Balance>("/balance"))) throw new Error("Test payments unavailable");
      const scope = `checkout:${deviceId()}`;
      const key = retryKeys.get(scope, { pack });
      let result: { url: string; order_id: number | string; mode?: string };
      try { result = await request<{ url: string; order_id: number | string; mode?: string }>("/checkout", { method: "POST", body: JSON.stringify({ pack }), headers: { "Idempotency-Key": key } }); }
      catch (error) {
        if (error instanceof CheckoutStateError) {
          retryKeys.bindOrder(scope, key, error.orderId);
          if (error.status !== "pending") retryKeys.complete(scope, error.orderId);
        }
        throw error;
      }
      if (result.mode !== "test") throw new Error("Test payment confirmation missing");
      const url = testCheckoutUrl(result.url);
      retryKeys.bindOrder(scope, key, String(result.order_id));
      return url;
    },
    status: async (orderId) => {
      if (!orderId || !/^[a-zA-Z0-9_-]+$/.test(orderId)) throw new Error("Invalid order");
      const result = await request<{ status: PaymentStatus; mode?: string }>(`/orders/${encodeURIComponent(orderId)}`);
      if (result.mode !== "test" || !["pending", "paid", "failed"].includes(result.status)) throw new Error("Unverified payment status");
      return result.status;
    },
  };
}
export const billingApi = createBillingAdapter(API_BASE, getDeviceId);
