"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ziweiApi, type ConversationOut } from "@/lib/ziwei/api";
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
  const [failedId, setFailedId] = useState<number | null>(null);
  const active = useRef(false);
  const currentProfile = useRef(profileId);
  currentProfile.current = profileId;
  const listVersion = useRef(0);
  const detailVersion = useRef(0);
  const listController = useRef<AbortController | null>(null);
  const detailController = useRef<AbortController | null>(null);

  const cancelRequests = useCallback(() => {
    ++listVersion.current; ++detailVersion.current;
    listController.current?.abort(); detailController.current?.abort();
  }, []);
  const refresh = useCallback(async () => {
    const version = ++listVersion.current;
    listController.current?.abort();
    const controller = new AbortController();
    listController.current = controller;
    setLoading(true); setError(null);
    const current = () => active.current && currentProfile.current === profileId
      && listVersion.current === version && !controller.signal.aborted;
    try {
      const rows = await ziweiApi.listConversations(profileId, controller.signal);
      if (current()) setConversations(rows);
    } catch {
      if (current()) setError("加载历史会话失败，请重试。");
    } finally {
      if (current()) setLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    active.current = true;
    setConversations([]); setLoadingId(null); setFailedId(null);
    void refresh();
    return () => { active.current = false; cancelRequests(); };
  }, [profileId, refresh, cancelRequests]);

  const close = () => {
    active.current = false;
    cancelRequests();
    onClose();
  };
  const handleOpen = async (conversationId: number) => {
    const version = ++detailVersion.current;
    detailController.current?.abort();
    const controller = new AbortController();
    detailController.current = controller;
    setLoadingId(conversationId); setFailedId(null);
    const current = () => active.current && currentProfile.current === profileId
      && detailVersion.current === version && !controller.signal.aborted;
    try {
      const rows = await ziweiApi.listMessages(conversationId, controller.signal);
      if (!current()) return;
      const mapped: ChatMessage[] = rows.map((m) => ({
        id: String(m.id), role: m.role === "user" ? "user" : "assistant", content: m.content,
        segments: m.chart_context_json?.segments, cameras: m.chart_context_json?.camera_commands,
      }));
      active.current = false;
      cancelRequests();
      onLoad(conversationId, mapped);
    } catch {
      if (current()) setFailedId(conversationId);
    } finally {
      if (current()) setLoadingId(null);
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
          onClick={close}
          className="rounded-md px-2 py-0.5 text-sm text-violet-300/70 transition-colors hover:text-violet-100"
        >
          返回
        </button>
      </div>

      {/* 列表 */}
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto bg-[#0a0618] px-3 py-3">
        {loading && <p role="status" className="animate-pulse px-1 text-sm text-violet-300/70">加载历史会话……</p>}
        {error && <div><p className="px-1 text-xs text-rose-400" role="alert">{error}</p>
          <button type="button" className="rounded border border-violet-400/40 px-3 py-2 text-sm text-violet-100" onClick={() => void refresh()}>重试加载历史会话</button></div>}
        {failedId !== null && <div><p className="px-1 text-xs text-rose-400" role="alert">打开会话失败，当前对话未改变。</p>
          <button type="button" className="rounded border border-violet-400/40 px-3 py-2 text-sm text-violet-100" onClick={() => void handleOpen(failedId)}>重试打开会话</button></div>}
        {!loading && !error && conversations.length === 0 ? (
          <p className="px-1 text-xs leading-relaxed text-violet-300/60">还没有历史会话</p>
        ) : (
          conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              aria-label={`打开历史会话 ${c.id} ${c.title || "未命名解读"}`}
              aria-busy={loadingId === c.id}
              onClick={() => void handleOpen(c.id)}
              className="flex min-w-0 flex-col gap-1 break-words rounded-xl border border-violet-500/20 px-3 py-2.5 text-left transition-colors hover:bg-violet-600/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="text-sm text-violet-100">{c.title || "未命名解读"}</span>
              <span className="flex items-center gap-2 text-[11px] text-violet-300/60">
                {SCENARIO_LABELS[c.scenario] ? (
                  <span className="rounded bg-violet-600/20 px-1.5 py-0.5 text-violet-200/70">
                    {SCENARIO_LABELS[c.scenario]}
                  </span>
                ) : null}
                <span>{formatTime(c.created_at)}</span>
                {loadingId === c.id ? <span role="status" className="text-violet-300/80">打开中…</span> : null}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
