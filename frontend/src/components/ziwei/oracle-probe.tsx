"use client";

import { useEffect, useState } from "react";
import { ziweiApi, ZiweiApiError, type OracleReply } from "@/lib/ziwei/api";

export function OracleProbe({ profileId }: { profileId: number }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState<OracleReply | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);

  // Reset conversation when profile changes
  useEffect(() => {
    setConversationId(null);
    setReply(null);
    setError(null);
  }, [profileId]);

  const handleSubmit = async () => {
    const message = input.trim();
    if (!message || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await ziweiApi.askOracle(profileId, {
        scenario: "natal",
        message,
        conversation_id: conversationId ?? undefined,
      });
      setReply(result);
      setConversationId(result.conversation_id);
      setInput("");
    } catch (e) {
      if (e instanceof ZiweiApiError) {
        if (e.status === 503) setError("解盘师未启用（缺少 API Key）");
        else if (e.status === 429) setError("今日额度已用尽，请明日再来");
        else setError("解盘暂不可用，请稍后再试");
      } else {
        setError("解盘暂不可用，请稍后再试");
      }
    } finally {
      setLoading(false);
    }
  };

  const formatCameraCommands = (cmds: OracleReply["camera_commands"]) => {
    if (!cmds || cmds.length === 0) return null;
    const labels = cmds.map((c) => {
      if (c.type === "focus_palace") return `飞入${c.palace}`;
      if (c.type === "overview") return "回到总览";
      if (c.type === "explain_term") return `释义：${c.term}`;
      return (c as { type: string }).type;
    });
    return `镜头：${labels.join("、")}`;
  };

  return (
    <div className="mt-4 rounded-[20px] border border-violet-500/20 bg-[#120a2e]/80 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-violet-400">问解盘师</p>

      {/* Reply area */}
      {reply && (
        <div className="mb-4 space-y-2">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-violet-100">{reply.response}</p>
          <div className="space-y-0.5 text-[11px] text-violet-400/60">
            {formatCameraCommands(reply.camera_commands) && (
              <p>{formatCameraCommands(reply.camera_commands)}</p>
            )}
            <p>
              {[
                reply.meta.model,
                reply.meta.total_tokens != null ? `${reply.meta.total_tokens} tokens` : null,
                reply.meta.latency_ms != null ? `${reply.meta.latency_ms} ms` : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="mb-3 text-xs text-rose-400" role="alert">
          {error}
        </p>
      )}

      {/* Input row */}
      <div className="flex gap-2">
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSubmit();
            }
          }}
          placeholder="向解盘师提问……（Enter 发送，Shift+Enter 换行）"
          className="flex-1 resize-none rounded-xl border border-violet-500/20 bg-[#0a0618] px-3 py-2 text-sm text-violet-100 placeholder-violet-400/40 outline-none focus:border-violet-500/50"
        />
        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={() => void handleSubmit()}
          className="self-end rounded-xl border border-violet-500/40 bg-violet-600/20 px-4 py-2 text-sm font-medium text-violet-300 transition-colors hover:bg-violet-600/30 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "解盘中…" : "问解盘师"}
        </button>
      </div>
    </div>
  );
}
