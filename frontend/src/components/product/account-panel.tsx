"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { PaidPreviewNotice } from "./preview-notice";
import { accountRequest, clearPaidRetryState, notifyPaidAccountChange, type AccountSession } from "@/lib/product/account";

export function PaidAccountPanel({ onAuthenticated }: { onAuthenticated?: () => void }) {
  const [session, setSession] = useState<AccountSession | null>(null);
  const [email, setEmail] = useState("");
  const [challenge, setChallenge] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const busyRef = useRef(false);
  const requestRef = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    accountRequest<AccountSession>("/session", undefined, controller.signal).then(value => {
      setSession(value);
      if (value.authenticated && value.enabled) onAuthenticated?.();
    }).catch(error => { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "暂时无法检查登录状态。"); });
    return () => { controller.abort(); requestRef.current?.abort(); };
  }, [onAuthenticated]);

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setMessage("");
    const controller = new AbortController(); requestRef.current = controller;
    try { await action(controller.signal); }
    catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "操作失败，请重试。"); }
    finally { if (!controller.signal.aborted) { busyRef.current = false; setBusy(false); } }
  }
  async function logout(all: boolean, signal: AbortSignal) {
    await accountRequest(all ? "/logout-all" : "/logout", {}, signal);
    clearPaidRetryState(); notifyPaidAccountChange(); window.location.assign("/account");
  }
  const field = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-ink focus-visible:outline-violet-600";
  const button = "min-h-11 rounded-lg border border-violet-300 px-3 py-2 text-violet-800 disabled:opacity-50";
  return <section aria-label="邮箱账号" className="mx-auto max-w-xl rounded-2xl border border-violet-200 bg-white p-6 text-ink shadow-sm">
    <h1 className="text-2xl font-semibold">邮箱账号</h1>
    <p className="mt-3 text-sm text-ink/70">一个邮箱，连接紫微与灵签。登录后，档案、记录与点数归属于同一个账号。</p>
    <div className="mt-4"><PaidPreviewNotice /></div>
    {session?.authenticated ? <div className="mt-5 space-y-4">
      <p role="status">已登录</p>
      {session.enabled ? <div className="flex flex-wrap gap-3"><Link href="/ziwei" className={button}>紫微斗数</Link><Link href="/qian" className={button}>灵签求签</Link><Link href="/credits" className={button}>点数与订单</Link></div> : <p>账号功能暂未开放，仍可退出登录。</p>}
      <div className="flex flex-wrap gap-3"><button className={button} disabled={busy} onClick={() => void run(signal => logout(false, signal))}>退出此浏览器</button><button className={button} disabled={busy} onClick={() => void run(signal => logout(true, signal))}>退出所有浏览器</button></div>
    </div> : session === null ? <p role="status" className="mt-5 text-sm text-ink/80">{message ? "暂时无法确认账号状态，请重试。" : "正在确认账号是否开放…"}</p> : session.enabled === false ? <div className="mt-5 space-y-3"><p role="status" className="font-medium">邮箱登录尚未开放，预览期间暂不保存个人记录。</p><p className="text-sm leading-relaxed text-ink/80">现在可以先了解紫微和灵签的区别。无需填写邮箱、提供付款信息或反复尝试登录。</p><Link href="/features" className={`${button} inline-flex items-center`}>返回探索功能</Link></div> : <form className="mt-5 space-y-4" onSubmit={event => {
      event.preventDefault(); void run(async signal => {
        if (challenge) {
          await accountRequest("/verify", { challenge_id: challenge, code }, signal);
          clearPaidRetryState(); setCode(""); setChallenge(""); setSession({ authenticated: true, enabled: true });
          notifyPaidAccountChange(); onAuthenticated?.();
        } else {
          const result = await accountRequest<{ challenge_id: string; expires_in: number }>("/challenges", { email }, signal);
          setChallenge(result.challenge_id); setMessage("请查看邮箱并粘贴验证码，15 分钟内有效。");
        }
      });
    }}>
      <label className="block text-sm">邮箱<input aria-describedby="account-email-help" className={field} required type="email" autoComplete="email" maxLength={255} value={email} disabled={busy || !!challenge} onChange={event => setEmail(event.target.value)} /></label>
      <p id="account-email-help" className="text-xs leading-relaxed text-ink/75">只在账号开放时发送登录验证码，不要求密码或付款信息。</p>
      {challenge && <label className="block text-sm">验证码<input className={field} required autoComplete="one-time-code" maxLength={128} value={code} disabled={busy} onChange={event => setCode(event.target.value.trim())} /></label>}
      <p className="text-xs text-ink/65">首次验证会创建新账号；再次验证会登录同一账号并退出其他浏览器。请只在本站输入验证码，不要分享给他人。</p>
      <div className="flex flex-wrap gap-3"><button type="submit" className={button} disabled={busy || session === null}>{busy ? "处理中…" : challenge ? "验证并登录" : "发送验证码"}</button>
      {challenge && <button type="button" className={button} disabled={busy} onClick={() => { setChallenge(""); setCode(""); setMessage(""); }}>更换邮箱 / 重新获取</button>}</div>
    </form>}
    {session === null && message && <button className={`${button} mt-4`} disabled={busy} onClick={() => void run(signal => logout(false, signal))}>清除本浏览器登录状态</button>}
    {message && <p role="status" className="mt-4 text-sm">{message}</p>}
  </section>;
}
