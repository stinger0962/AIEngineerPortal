"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { accountRequest, clearPaidRetryState, syncPaidAccountSession, type AccountSession } from "@/lib/product/account";
import type { ProductFeature } from "@/lib/product/config";
import { PaidAccountPanel } from "./account-panel";

export function PaidAccountGate({ children, feature }: { children: React.ReactNode; feature?: ProductFeature }) {
  const [session, setSession] = useState<AccountSession | null>(null);
  const [checking, setChecking] = useState(true);
  const requestRef = useRef<AbortController | null>(null);
  const refresh = useCallback(() => {
    requestRef.current?.abort();
    const controller = new AbortController(); requestRef.current = controller;
    setChecking(true);
    accountRequest<AccountSession>("/session", undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) { syncPaidAccountSession(value.authenticated && Number.isInteger(value.account_id) ? value.account_id! : null); setSession(value); } })
      .catch(() => { if (!controller.signal.aborted) setSession(null); })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
  }, []);
  useEffect(() => {
    refresh();
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    const invalidate = () => { requestRef.current?.abort(); clearPaidRetryState(); setSession(null); setChecking(false); };
    window.addEventListener("focus", refresh);
    window.addEventListener("pageshow", refresh);
    window.addEventListener("paid-account-changed", refresh);
    window.addEventListener("paid-session-invalid", invalidate);
    document.addEventListener("visibilitychange", visible);
    let channel: BroadcastChannel | undefined;
    try { channel = new BroadcastChannel("paid-account"); channel.onmessage = refresh; } catch { /* focus remains */ }
    return () => {
      requestRef.current?.abort(); channel?.close();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("pageshow", refresh);
      window.removeEventListener("paid-account-changed", refresh);
      window.removeEventListener("paid-session-invalid", invalidate);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [refresh]);
  const authenticated = session?.authenticated && session.enabled && Number.isInteger(session.account_id);
  return <>
    {checking && <p role="status" className="p-4 text-sm text-ink/65">正在检查登录状态…</p>}
    {authenticated ? <div key={session.account_id} hidden={checking}>{children}</div>
      : <div hidden={checking}>
        {feature && <section aria-label="当前体验" className="mx-auto mb-5 max-w-xl rounded-xl border border-violet-200 bg-white/70 p-5">
          <p className="text-sm text-violet-900">你选择了 · {feature.english}</p>
          <h2 className="mt-1 text-xl font-semibold">{feature.label}</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink/85">{feature.purpose}</p>
          <p className="mt-2 text-sm leading-relaxed text-ink/75">{feature.preparation}</p>
        </section>}
        <PaidAccountPanel onAuthenticated={refresh} />
      </div>}
  </>;
}
