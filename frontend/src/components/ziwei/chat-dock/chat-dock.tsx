"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ziweiApi, ZiweiApiError } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "@/components/ziwei/term-card";
import type { ChatMessage, DockState } from "./types";
import { fireCamera } from "./camera";
import { PersonaSwitch } from "./persona-switch";
import { HistoryPanel } from "./history-panel";

type ChatDockProps = {
  profileId: number;
  persona: string;
  chart: ZiweiChart;
  onFocusBranch: (branch: string | null) => void; // Task 5 回放镜头用
  onTerm: (t: TermInfo | null) => void; // Task 5 回放术语卡用
  onPersonaChange: (next: string) => void; // Task 6 persona 切换冒泡
};

export function ChatDock({ profileId, persona, chart, onFocusBranch, onTerm, onPersonaChange }: ChatDockProps) {
  const [dock, setDock] = useState<DockState>("normal");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null); // 中止进行中的流式解盘

  const handlePersonaChanged = (next: string) => {
    onPersonaChange(next);
    // Persona change requires a fresh conversation context (new system prompt voice)
    setConversationId(null);
  };

  // 档案切换时重置对话——渲染期重置（避免 effect 滞后一帧）
  const [prevId, setPrevId] = useState(profileId);
  if (prevId !== profileId) {
    setPrevId(profileId);
    abortRef.current?.abort(); // 切档案时中止上一条流，避免镜头/文本串台
    setMessages([]);
    setConversationId(null);
    setError(null);
    setInput("");
    setShowHistory(false);
  }

  // 载入历史会话：直接展示（不回放），并以该会话 id 续聊
  const handleLoadConversation = (loadedConversationId: number, mapped: ChatMessage[]) => {
    abortRef.current?.abort();
    setMessages(mapped);
    setConversationId(loadedConversationId);
    setShowHistory(false);
  };

  // 自动滚动到最新消息
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, loading]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    abortRef.current?.abort(); // 新提问时中止仍在流的上一条
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);
    setLoading(true); // 首段文字到达前显示「凝神观盘」
    setError(null);
    setInput("");

    const reqProfileId = profileId;
    const stale = () => reqProfileId !== profileId || controller.signal.aborted;
    let acc = "";
    let gotText = false;

    try {
      await ziweiApi.streamOracle(
        profileId,
        { scenario: "natal", message, conversation_id: conversationId ?? undefined },
        {
          onText: (delta) => {
            if (stale()) return;
            gotText = true;
            setLoading(false);
            acc += delta;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m)),
            );
          },
          onCamera: (cmd) => {
            if (stale()) return;
            fireCamera(cmd, { chart, onFocusBranch, onTerm });
          },
          onDone: (cid) => {
            if (stale()) return;
            setConversationId(cid);
            setLoading(false);
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, pending: false } : m)),
            );
          },
          onError: () => {
            if (controller.signal.aborted) return;
            // 后端已尽力保住半截；保留已铺文本、停笔；全空则提示失败
            setLoading(false);
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, pending: false } : m)),
            );
            if (!gotText) setError("解盘暂不可用，请稍后再试");
          },
        },
        controller.signal,
      );
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return; // 主动中止，静默
      // 开流前的校验错误：移除空的助手气泡并本地化提示
      setMessages((prev) => prev.filter((m) => !(m.id === assistantId && m.content === "")));
      if (e instanceof ZiweiApiError) {
        if (e.status === 503) setError("解盘师未启用（缺少 API Key）");
        else if (e.status === 429) setError("今日额度已用尽，请明日再来");
        else setError("解盘暂不可用，请稍后再试");
      } else {
        setError("解盘暂不可用，请稍后再试");
      }
      setLoading(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  // —— 折叠态：右下角圆钮
  if (dock === "collapsed") {
    return (
      <button
        type="button"
        aria-label="展开解盘师"
        onClick={() => setDock("normal")}
        className="absolute bottom-4 right-4 z-20 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-600 text-lg text-white shadow-[0_8px_30px_rgba(91,33,182,0.55)] transition-transform hover:scale-105"
      >
        ✦
      </button>
    );
  }

  const cardBase =
    "flex flex-col border border-violet-500/30 bg-[#120a2e]/95 backdrop-blur shadow-[0_8px_30px_rgba(91,33,182,0.45)]";
  const containerClass =
    dock === "expanded"
      ? `absolute inset-y-0 right-0 z-30 w-full sm:w-[380px] rounded-l-[20px] ${cardBase}`
      : `absolute bottom-4 right-4 z-20 w-[min(340px,90vw)] max-h-[70%] rounded-[20px] ${cardBase}`;

  return (
    <div className={containerClass}>
      {/* 顶栏 */}
      <div className="flex flex-col gap-1.5 border-b border-violet-500/20 px-4 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold tracking-wide text-violet-100">✦ 解盘师</span>
          <div className="flex items-center gap-1">
            {dock === "normal" ? (
              <>
                <button
                  type="button"
                  aria-label="全屏对话"
                  onClick={() => setDock("expanded")}
                  className="rounded-md px-1.5 py-0.5 text-violet-300/70 transition-colors hover:text-violet-100"
                >
                  ⤢
                </button>
                <button
                  type="button"
                  aria-label="收起解盘师"
                  onClick={() => setDock("collapsed")}
                  className="rounded-md px-1.5 py-0.5 text-violet-300/70 transition-colors hover:text-violet-100"
                >
                  ﹣
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  aria-label="历史会话"
                  onClick={() => setShowHistory(true)}
                  className="rounded-md px-1.5 py-0.5 text-violet-300/70 transition-colors hover:text-violet-100"
                >
                  历史
                </button>
                <button
                  type="button"
                  aria-label="缩小对话"
                  onClick={() => setDock("normal")}
                  className="rounded-md px-1.5 py-0.5 text-violet-300/70 transition-colors hover:text-violet-100"
                >
                  ⤡
                </button>
              </>
            )}
          </div>
        </div>
        <PersonaSwitch profileId={profileId} persona={persona} onChanged={handlePersonaChanged} />
      </div>

      {showHistory && dock === "expanded" ? (
        <HistoryPanel
          profileId={profileId}
          onClose={() => setShowHistory(false)}
          onLoad={handleLoadConversation}
        />
      ) : (
        <>
      {/* 消息区 */}
      <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !loading ? (
          <p className="text-xs leading-relaxed text-violet-300/60">
            向解盘师提问，例如「我今年的事业运如何？」
          </p>
        ) : null}
        {messages.map((m) =>
          m.role === "user" ? (
            <div
              key={m.id}
              className="max-w-[85%] self-end rounded-xl bg-violet-600/30 px-3 py-2 text-sm text-violet-50"
            >
              {m.content}
            </div>
          ) : (
            <div key={m.id} className="whitespace-pre-wrap text-sm leading-relaxed text-violet-100">
              {m.content}
              {m.pending ? (
                <span className="animate-pulse text-violet-300/70">▌</span>
              ) : null}
            </div>
          ),
        )}
        {loading ? (
          <p className="animate-pulse text-sm text-violet-300/70">解盘师凝神观盘……</p>
        ) : null}
        {error ? (
          <p className="text-xs text-rose-400" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      {/* 输入区 */}
      <div className="flex items-end gap-2 border-t border-violet-500/20 px-3 py-3">
        <textarea
          rows={dock === "expanded" ? 3 : 2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="向解盘师提问……（Enter 发送，Shift+Enter 换行）"
          className="flex-1 resize-none rounded-xl border border-violet-500/20 bg-[#0a0618] px-3 py-2 text-sm text-violet-100 placeholder-violet-400/40 outline-none focus:border-violet-500/50"
        />
        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={() => void handleSend()}
          className="self-end rounded-xl border border-violet-500/40 bg-violet-600/20 px-4 py-2 text-sm font-medium text-violet-300 transition-colors hover:bg-violet-600/30 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "解盘中…" : "问"}
        </button>
      </div>
        </>
      )}
    </div>
  );
}
