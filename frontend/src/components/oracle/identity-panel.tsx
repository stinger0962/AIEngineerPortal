"use client";

import { useEffect, useState } from "react";
import { KeyRound, Copy, Check, ChevronDown, ShieldCheck } from "lucide-react";
import { getDeviceId, setDeviceId } from "@/lib/deviceId";
import { ziweiApi } from "@/lib/ziwei/api";

/** 命理隐私：展示本浏览器的匿名「找回码」（device id），提示保存；并提供换设备恢复
 *  与一次性认领旧数据。命理数据只归属这台浏览器，别人看不到你的。
 *  暗紫玻璃风，与 玄域 建档卡 / 星盘台同一套视觉语言。 */
export function OracleIdentityPanel() {
  const [id, setId] = useState("");
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const [pasteCode, setPasteCode] = useState("");
  const [claimCode, setClaimCode] = useState("");
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => setId(getDeviceId()), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  function restore() {
    if (setDeviceId(pasteCode)) {
      window.location.reload();
    } else {
      setMsg({ text: "找回码无效。", ok: false });
    }
  }

  async function claim() {
    setMsg(null);
    try {
      const r = await ziweiApi.claimLegacy(claimCode.trim());
      setMsg({ text: `已认领 ${r.claimed_profiles} 个命主档案、${r.claimed_readings} 条求签记录，正在刷新…`, ok: true });
      setTimeout(() => window.location.reload(), 900);
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : "认领失败。", ok: false });
    }
  }

  const fieldCls =
    "flex-1 min-w-0 rounded-lg border border-violet-300/15 bg-[#0c0620] px-2.5 py-1.5 text-[12px] text-violet-50 placeholder:text-violet-200/30 focus:outline-none focus:ring-2 focus:ring-violet-400/40 focus:border-violet-400/40";
  const btnCls =
    "shrink-0 rounded-lg border border-violet-300/25 bg-violet-400/5 px-2.5 py-1.5 text-[12px] font-medium text-violet-100 transition-colors hover:bg-violet-400/15 disabled:opacity-35 disabled:hover:bg-violet-400/5";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-violet-300/15 bg-gradient-to-b from-[#140a2e] to-[#0a0618] p-4 shadow-[0_10px_30px_-18px_rgba(124,58,237,0.7)]">
      {/* faint aura */}
      <div className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-violet-500/20 blur-2xl" />

      <div className="relative space-y-2.5">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-violet-400/15 text-violet-200">
            <KeyRound size={13} strokeWidth={2.2} />
          </span>
          <span className="text-[13px] font-semibold tracking-wide text-violet-50">你的找回码</span>
          <span className="ml-auto rounded-full border border-amber-300/25 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium tracking-wide text-amber-200/90">
            务必保存
          </span>
        </div>

        <div className="flex items-center gap-2">
          <code className="flex-1 min-w-0 truncate rounded-lg border border-violet-300/15 bg-[#0c0620] px-2.5 py-1.5 font-mono text-[12px] tracking-tight text-violet-100/85">
            {id || "…"}
          </code>
          <button onClick={copy} className={`flex items-center gap-1 ${btnCls}`} aria-label="复制找回码">
            {copied ? <Check size={13} className="text-emerald-300" /> : <Copy size={13} />}
            {copied ? "已复制" : "复制"}
          </button>
        </div>

        <p className="flex gap-1.5 text-[11px] leading-5 text-violet-100/45">
          <ShieldCheck size={13} className="mt-0.5 shrink-0 text-violet-300/60" />
          <span>
            命理数据只归属这台浏览器——别人在自己设备上看不到你的档案。
            <span className="text-violet-100/70">换设备 / 清缓存会看不到旧记录，把这串码存好，用它找回。</span>
          </span>
        </p>

        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1 pt-0.5 text-[12px] font-medium text-violet-200/70 transition-colors hover:text-violet-100"
        >
          <ChevronDown size={13} className={`transition-transform ${open ? "rotate-180" : ""}`} />
          换设备找回 · 认领旧档案
        </button>

        {open && (
          <div className="space-y-3 border-t border-violet-300/10 pt-3">
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold text-violet-100/55">粘贴找回码，在本设备恢复访问</p>
              <div className="flex items-center gap-2">
                <input
                  value={pasteCode}
                  onChange={(e) => setPasteCode(e.target.value)}
                  placeholder="粘贴之前保存的找回码…"
                  className={fieldCls}
                />
                <button onClick={restore} disabled={!pasteCode.trim()} className={btnCls}>
                  恢复
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold text-violet-100/55">认领无归属旧数据（需服务器口令）</p>
              <div className="flex items-center gap-2">
                <input
                  value={claimCode}
                  onChange={(e) => setClaimCode(e.target.value)}
                  placeholder="认领口令…"
                  className={fieldCls}
                />
                <button onClick={claim} disabled={!claimCode.trim()} className={btnCls}>
                  认领
                </button>
              </div>
            </div>
          </div>
        )}

        {msg && (
          <p className={`text-[11px] leading-5 ${msg.ok ? "text-emerald-300" : "text-rose-300"}`}>{msg.text}</p>
        )}
      </div>
    </div>
  );
}
