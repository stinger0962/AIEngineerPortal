"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ziweiApi, ZiweiApiError } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "@/components/ziwei/term-card";
import type { ChatMessage, DockState } from "./types";
import { useSegmentReplay } from "./use-segment-replay";
import { PersonaSwitch } from "./persona-switch";

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

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const replay = useSegmentReplay();

  const handlePersonaChanged = (next: string) => {
    onPersonaChange(next);
    // Persona change requires a fresh conversation context (new system prompt voice)
    setConversationId(null);
  };

  // 档案切换时重置对话——渲染期重置（避免 effect 滞后一帧）
  const [prevId, setPrevId] = useState(profileId);
  if (prevId !== profileId) {
    setPrevId(profileId);
    replay.cancel(); // 切档案时中止上一条回放，避免镜头/文本串台
    setMessages([]);
    setConversationId(null);
    setError(null);
    setInput("");
  }

  // 自动滚动到最新消息
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, loading]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    replay.cancel(); // 新提问时中止仍在播放的上一条回放

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);
    setInput("");

    const reqProfileId = profileId;
    try {
      const reply = await ziweiApi.askOracle(profileId, {
        scenario: "natal",
        message,
        conversation_id: conversationId ?? undefined,
      });
      // 网络等待期间若切换了档案，丢弃这条过期回复
      if (reqProfileId !== profileId) return;

      setConversationId(reply.conversation_id);
      const segs =
        reply.segments && reply.segments.length
          ? reply.segments
          : [{ text: reply.response, commands: reply.camera_commands }];

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          segments: reply.segments,
          cameras: reply.camera_commands,
          pending: true,
        },
      ]);
      // 回复已到达：停掉加载态，转入逐段回放（打字 + 镜头）
      setLoading(false);

      const reduced =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      await replay.play(segs, {
        chart,
        onText: (full) =>
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: full } : m)),
          ),
        onFocusBranch,
        onTerm,
        reducedMotion: reduced,
      });

      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, pending: false } : m)),
      );
    } catch (e) {
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
              <button
                type="button"
                aria-label="缩小对话"
                onClick={() => setDock("normal")}
                className="rounded-md px-1.5 py-0.5 text-violet-300/70 transition-colors hover:text-violet-100"
              >
                ⤡
              </button>
            )}
          </div>
        </div>
        <PersonaSwitch profileId={profileId} persona={persona} onChanged={handlePersonaChanged} />
      </div>

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
    </div>
  );
}
