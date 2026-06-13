"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ziweiApi, ZiweiApiError } from "@/lib/ziwei/api";
import type { CameraCommand } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "@/components/ziwei/term-card";
import { fireCamera } from "./camera";
import type { ChatMessage, DockState } from "./types";
import { useOracleTour } from "./use-oracle-tour";
import { PersonaSwitch } from "./persona-switch";
import { HistoryPanel } from "./history-panel";
import { stripMarkdown } from "@/lib/ziwei/text";

type ChatDockProps = {
  profileId: number;
  persona: string;
  chart: ZiweiChart;
  onFocusBranch: (branch: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  onPersonaChange: (next: string) => void;
  onTourActiveChange: (active: boolean) => void;
};

export function ChatDock({ profileId, persona, chart, onFocusBranch, onTerm, onPersonaChange, onTourActiveChange }: ChatDockProps) {
  const [dock, setDock] = useState<DockState>("normal");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null); // 中止进行中的流式解盘

  const tour = useOracleTour();
  const [caption, setCaption] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [audioHintSeen, setAudioHintSeen] = useState(true); // 默认不显，挂载后读 localStorage 决定

  useEffect(() => {
    try {
      setAudioHintSeen(window.localStorage.getItem("ziwei-audio-hint") === "1");
    } catch {
      setAudioHintSeen(true);
    }
  }, []);

  const dismissAudioHint = () => {
    setAudioHintSeen(true);
    try { window.localStorage.setItem("ziwei-audio-hint", "1"); } catch { /* 隐私模式忽略 */ }
  };

  const toggleMuted = () => {
    const next = !muted;
    setMuted(next);
    tour.setMuted(next);
  };

  const fireCommand = (cmd: CameraCommand) => {
    if (cmd.type === "overview") { onFocusBranch(null); onTerm(null); return; }
    fireCamera(cmd, { chart, onFocusBranch, onTerm });
  };

  const handlePersonaChanged = (next: string) => {
    onPersonaChange(next);
    // 切人设需要全新的会话上下文（system prompt 声口变了）；并中止进行中的解读，
    // 否则旧 tour 收尾时的 setConversationId(queue.convId) 会把这里清的 null 又覆盖回去。
    abortRef.current?.abort();
    tour.cancel();
    setCaption(null);
    setLoading(false);
    setConversationId(null);
  };

  // 档案切换时重置对话——渲染期重置（避免 effect 滞后一帧）
  const [prevId, setPrevId] = useState(profileId);
  if (prevId !== profileId) {
    setPrevId(profileId);
    abortRef.current?.abort(); // 切档案时中止上一条流，避免镜头/文本串台
    tour.cancel();
    setMessages([]);
    setConversationId(null);
    setError(null);
    setInput("");
    setCaption(null);
    setLoading(false); // 中止进行中的解读后解锁输入（abort 走 AbortError 分支不复位 loading）
    setShowHistory(false);
  }

  // 历史「重新解读」：用已存 segments 重跑编排（不调 AI、不入库）。
  const replayMessage = (m: ChatMessage) => {
    if (!m.segments || m.segments.length === 0) return;
    abortRef.current?.abort();
    tour.cancel();
    setCaption(null);
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const queue = tour.beginFromSegments(m.segments);
    tour.setMuted(muted);
    void tour.play(queue, {
      fireCommand,
      onCaption: setCaption,
      onReveal: () => { /* 历史正文已在气泡，无需改写 */ },
      onTourActiveChange,
      reducedMotion: reduced,
    });
  };

  // 载入历史会话：直接展示（不回放），并以该会话 id 续聊
  const handleLoadConversation = (loadedConversationId: number, mapped: ChatMessage[]) => {
    abortRef.current?.abort();
    tour.cancel();
    setCaption(null);
    setLoading(false); // 中止进行中的解读后解锁输入
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

    abortRef.current?.abort();
    tour.cancel();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);
    setLoading(true);
    setError(null);
    setInput("");
    setCaption(null);

    const reqProfileId = profileId;
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const { queue, handlers } = tour.begin();
    tour.setMuted(muted);

    const setAssistant = (content: string, pending: boolean) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content, pending } : m)));

    const playPromise = tour.play(queue, {
      fireCommand,
      onCaption: (c) => { if (reqProfileId === profileId) setCaption(c); },
      onReveal: (full) => { if (reqProfileId === profileId) { setLoading(false); setAssistant(full, false); } },
      onTourActiveChange,
      reducedMotion: reduced,
    });

    try {
      await ziweiApi.streamOracle(profileId, { scenario: "natal", message, conversation_id: conversationId ?? undefined }, handlers, controller.signal);
    } catch (e) {
      tour.cancel(); // 关队列让 play 退出（校验错误或 abort）
      if (e instanceof DOMException && e.name === "AbortError") { await playPromise; return; }
      setMessages((prev) => prev.filter((m) => !(m.id === assistantId && m.content === "")));
      if (e instanceof ZiweiApiError) {
        if (e.status === 503) setError("解盘师未启用（缺少 API Key）");
        else if (e.status === 429) setError("今日额度已用尽，请明日再来");
        else setError("解盘暂不可用，请稍后再试");
      } else {
        setError("解盘暂不可用，请稍后再试");
      }
      setLoading(false);
      setCaption(null);
      await playPromise;
      return;
    }

    await playPromise;
    if (reqProfileId === profileId && queue.convId !== null) setConversationId(queue.convId);
    setLoading(false);
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
        {!audioHintSeen ? (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-violet-500/30 bg-violet-600/10 px-3 py-2 text-xs text-violet-200">
            <span>🔊 解读将有声朗读，可随时静音</span>
            <button type="button" onClick={dismissAudioHint} className="text-violet-300/70 hover:text-violet-100">知道了</button>
          </div>
        ) : null}
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
              {m.pending && !m.content ? (
                <div className="flex items-center gap-2 text-violet-300/80">
                  <span className="animate-pulse">✦ 解盘师正在解读{caption ?? ""}</span>
                  <button type="button" onClick={toggleMuted} aria-label={muted ? "取消静音" : "静音"} className="rounded px-1.5 py-0.5 text-xs text-violet-300/70 hover:text-violet-100">
                    {muted ? "🔇" : "🔊"}
                  </button>
                  <button type="button" onClick={tour.skip} className="rounded px-1.5 py-0.5 text-xs text-violet-300/70 hover:text-violet-100">
                    直接看文字
                  </button>
                </div>
              ) : (
                <>
                  {stripMarkdown(m.content)}
                  {m.pending ? <span className="animate-pulse text-violet-300/70">▌</span> : null}
                  {!m.pending && m.segments && m.segments.length > 0 ? (
                    <div className="mt-1">
                      <button type="button" onClick={() => replayMessage(m)} className="text-xs text-violet-300/60 hover:text-violet-100">
                        ▶ 重新解读
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          ),
        )}
        {loading && !messages.some((m) => m.role === "assistant" && m.pending) ? (
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
