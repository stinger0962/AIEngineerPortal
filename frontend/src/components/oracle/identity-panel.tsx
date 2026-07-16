"use client";

import { useEffect, useState } from "react";
import { KeyRound, Copy, Check, ChevronDown } from "lucide-react";
import { getDeviceId, setDeviceId } from "@/lib/deviceId";
import { ziweiApi } from "@/lib/ziwei/api";

/** 命理隐私：展示本浏览器的匿名「找回码」（device id），提示保存；并提供换设备恢复
 *  与一次性认领旧数据。命理数据只归属这台浏览器，别人看不到你的。 */
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

  return (
    <div className="rounded-2xl border border-violet-400/25 bg-violet-600/[0.04] p-4 space-y-2.5">
      <div className="flex items-center gap-2">
        <KeyRound size={15} className="text-violet-600" />
        <span className="text-sm font-semibold text-ink">你的找回码 · 务必保存</span>
      </div>
      <div className="flex items-center gap-2">
        <code className="flex-1 min-w-0 truncate rounded-lg bg-white/80 border border-ink/10 px-2.5 py-1.5 font-mono text-[12px] text-ink/70">
          {id || "…"}
        </code>
        <button
          onClick={copy}
          className="flex shrink-0 items-center gap-1 rounded-lg border border-violet-400/40 px-2.5 py-1.5 text-[12px] font-medium text-violet-600 transition-colors hover:bg-violet-600/5"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? "已复制" : "复制"}
        </button>
      </div>
      <p className="text-[11px] leading-5 text-ink/50">
        命理数据只归属这台浏览器——别人在自己设备上看不到你的档案。换设备 / 清了缓存会看不到旧记录，把这个码存好，用它找回。
      </p>

      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-[12px] font-medium text-violet-600/80 transition-colors hover:text-violet-600"
      >
        <ChevronDown size={13} className={`transition-transform ${open ? "rotate-180" : ""}`} />
        换设备找回 · 认领旧档案
      </button>

      {open && (
        <div className="space-y-3 pt-1">
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold text-ink/55">粘贴找回码，在本设备恢复访问</p>
            <div className="flex items-center gap-2">
              <input
                value={pasteCode}
                onChange={(e) => setPasteCode(e.target.value)}
                placeholder="粘贴之前保存的找回码…"
                className="flex-1 min-w-0 rounded-lg border border-ink/12 bg-white/80 px-2.5 py-1.5 text-[12px] text-ink focus:outline-none focus:ring-2 focus:ring-violet-400/40"
              />
              <button
                onClick={restore}
                disabled={!pasteCode.trim()}
                className="shrink-0 rounded-lg border border-violet-400/40 px-2.5 py-1.5 text-[12px] font-medium text-violet-600 transition-colors hover:bg-violet-600/5 disabled:opacity-40"
              >
                恢复
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold text-ink/55">认领无归属旧数据（需服务器口令）</p>
            <div className="flex items-center gap-2">
              <input
                value={claimCode}
                onChange={(e) => setClaimCode(e.target.value)}
                placeholder="认领口令…"
                className="flex-1 min-w-0 rounded-lg border border-ink/12 bg-white/80 px-2.5 py-1.5 text-[12px] text-ink focus:outline-none focus:ring-2 focus:ring-violet-400/40"
              />
              <button
                onClick={claim}
                disabled={!claimCode.trim()}
                className="shrink-0 rounded-lg border border-violet-400/40 px-2.5 py-1.5 text-[12px] font-medium text-violet-600 transition-colors hover:bg-violet-600/5 disabled:opacity-40"
              >
                认领
              </button>
            </div>
          </div>
        </div>
      )}

      {msg && (
        <p className={`text-[11px] leading-5 ${msg.ok ? "text-emerald-600" : "text-rose-500"}`}>{msg.text}</p>
      )}
    </div>
  );
}
