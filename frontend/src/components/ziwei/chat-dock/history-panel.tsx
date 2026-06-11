"use client";

import { useEffect, useState } from "react";
import { ziweiApi, ZiweiApiError, type ConversationOut } from "@/lib/ziwei/api";
import type { ChatMessage } from "./types";

type HistoryPanelProps = {
  profileId: number;
  onLoad: (conversationId: number, messages: ChatMessage[]) => void;
  onClose: () => void;
};

const SCENARIO_LABELS: Record<string, string> = {
  natal: "本命盘",
  decadal: "大限",
  yearly: "流年",
};

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString();
}

export function HistoryPanel({ profileId, onLoad, onClose }: HistoryPanelProps) {
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    ziweiApi
      .listConversations(profileId)
      .then((rows) => {
        if (cancelled) return;
        setConversations(rows);
      })
      .catch(() => {
        if (cancelled) return;
        setError("加载历史会话失败，请稍后再试");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  const handleOpen = async (conversationId: number) => {
    if (loadingId !== null) return;
    setLoadingId(conversationId);
    setError(null);
    try {
      const rows = await ziweiApi.listMessages(conversationId);
      const mapped: ChatMessage[] = rows.map((m) => ({
        id: String(m.id),
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
        segments: m.chart_context_json.segments,
        cameras: m.chart_context_json.camera_commands,
      }));
      onLoad(conversationId, mapped);
    } catch (e) {
      if (e instanceof ZiweiApiError) {
        setError("打开会话失败，请稍后再试");
      } else {
        setError("打开会话失败，请稍后再试");
      }
      setLoadingId(null);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-[#120a2e]">
      {/* 头部 */}
      <div className="flex items-center justify-between gap-2 border-b border-violet-500/20 px-4 py-2.5">
        <span className="text-sm font-semibold tracking-wide text-violet-100">历史会话</span>
        <button
          type="button"
          aria-label="返回当前对话"
          onClick={onClose}
          className="rounded-md px-2 py-0.5 text-sm text-violet-300/70 transition-colors hover:text-violet-100"
        >
          返回
        </button>
      </div>

      {/* 列表 */}
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto bg-[#0a0618] px-3 py-3">
        {loading ? (
          <p className="animate-pulse px-1 text-sm text-violet-300/70">加载历史会话……</p>
        ) : error ? (
          <p className="px-1 text-xs text-rose-400" role="alert">
            {error}
          </p>
        ) : conversations.length === 0 ? (
          <p className="px-1 text-xs leading-relaxed text-violet-300/60">还没有历史会话</p>
        ) : (
          conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              disabled={loadingId !== null}
              onClick={() => void handleOpen(c.id)}
              className="flex flex-col gap-1 rounded-xl border border-violet-500/20 px-3 py-2.5 text-left transition-colors hover:bg-violet-600/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="text-sm text-violet-100">{c.title || "未命名解读"}</span>
              <span className="flex items-center gap-2 text-[11px] text-violet-300/60">
                {SCENARIO_LABELS[c.scenario] ? (
                  <span className="rounded bg-violet-600/20 px-1.5 py-0.5 text-violet-200/70">
                    {SCENARIO_LABELS[c.scenario]}
                  </span>
                ) : null}
                <span>{formatTime(c.created_at)}</span>
                {loadingId === c.id ? <span className="text-violet-300/80">打开中…</span> : null}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
