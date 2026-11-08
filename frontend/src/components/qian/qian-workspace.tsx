"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { qianApi, QianApiError, type QianSign, type QianReadingOut, type QianReadingDetail } from "@/lib/qian/api";
import { useOracleTour } from "@/components/ziwei/chat-dock/use-oracle-tour";
import { TermCard, type TermInfo } from "@/components/ziwei/term-card";
import { makeQianFireCommand } from "./qian-camera";

// ── Font stacks ────────────────────────────────────────────────────────────────
const KAITI = "'STKaiti','KaiTi STD','KaiTi','楷体','Kaiti SC',serif";
const SONGTI = "'Songti SC','Noto Serif CJK SC','SimSun',serif";

// History list stays masked; authenticated owners explicitly open private details.
function MaskedQuestion({ text }: { text: string }) {
  return (
    <span className="ml-2" style={{ color: "rgba(233,220,196,.7)" }}>
      {text}
    </span>
  );
}

// ── Grade → badge palette ──────────────────────────────────────────────────────
function gradeBadge(grade: string): { bg: string; text: string } {
  if (grade.includes("上")) return { bg: "#b8862f", text: "#fff4dc" };
  if (grade.includes("下")) return { bg: "#8a3a22", text: "#e8c9a6" };
  return { bg: "#9c6b1a", text: "#f0dcae" };
}

const QianScene = dynamic(() => import("./scene3d/qian-scene"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] items-center justify-center">
      <p className="animate-pulse text-sm" style={{ color: "rgba(214,168,74,.7)" }}>
        正在备好签筒……
      </p>
    </div>
  ),
});

export function QianWorkspace() {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<"idle" | "shaking" | "reading">("idle");
  const [sign, setSign] = useState<QianSign | null>(null);
  const [answer, setAnswer] = useState("");
  const [term, setTerm] = useState<TermInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QianReadingOut[]>([]);
  const [historyState, setHistoryState] = useState<"loading" | "ready" | "error">("loading");
  const [expandedHistory, setExpandedHistory] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<QianReadingDetail | null>(null);
  const [detailState, setDetailState] = useState<"loading" | "ready" | "error">("loading");
  const [detailError, setDetailError] = useState("");
  const historyRequest = useRef(0);
  const detailRequest = useRef(0);
  const historyController = useRef<AbortController | null>(null);
  const detailController = useRef<AbortController | null>(null);
  const detailHeading = useRef<HTMLHeadingElement | null>(null);
  const detailTrigger = useRef<HTMLButtonElement | null>(null);
  const historyMounted = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const tour = useOracleTour();

  // 仅卸载时中止在途流 + 停指挥器。依赖稳定的 cancel（useOracleTour 每次渲染返回新对象字面量，
  // 用 [tour] 会让 cleanup 每次渲染都触发、把刚发起的流误中止）。cancel 是 useCallback 稳定引用。
  const { cancel: cancelTour } = tour;
  useEffect(() => () => { abortRef.current?.abort(); cancelTour(); }, [cancelTour]);

  useEffect(() => {
    historyMounted.current = true;
    return () => {
      historyMounted.current = false;
      ++historyRequest.current; ++detailRequest.current;
      historyController.current?.abort(); detailController.current?.abort();
    };
  }, []);

  const refreshHistory = useCallback(async () => {
    const request = ++historyRequest.current;
    historyController.current?.abort();
    const controller = new AbortController();
    historyController.current = controller;
    setHistoryState("loading");
    try {
      const rows = await qianApi.listReadings(controller.signal);
      if (!Array.isArray(rows)) throw new Error("Invalid history");
      if (historyMounted.current && request === historyRequest.current) {
        setHistory(rows.slice(0, 50)); setHistoryState("ready");
      }
    } catch {
      if (historyMounted.current && request === historyRequest.current && !controller.signal.aborted) {
        setHistory([]); setHistoryState("error");
      }
    }
  }, []);
  useEffect(() => { if (phase === "idle") void refreshHistory(); }, [phase, refreshHistory]);

  const openDetail = async (id: number) => {
    const request = ++detailRequest.current;
    detailController.current?.abort();
    const controller = new AbortController();
    detailController.current = controller;
    setSelectedId(id); setDetail(null); setDetailState("loading");
    try {
      const saved = await qianApi.getReading(id, controller.signal);
      if (historyMounted.current && request === detailRequest.current) {
        setDetail(saved); setDetailState("ready");
      }
    } catch (error) {
      if (historyMounted.current && request === detailRequest.current && !controller.signal.aborted) {
        setDetailError(error instanceof QianApiError && error.status === 404
          ? "记录不存在或已不可访问。" : "历史详情暂不可用，请重试。");
        setDetailState("error");
      }
    }
  };
  useEffect(() => { if (selectedId !== null) detailHeading.current?.focus(); }, [selectedId]);
  const closeDetail = () => {
    ++detailRequest.current; detailController.current?.abort();
    setSelectedId(null); setDetail(null);
    detailTrigger.current?.focus();
  };

  const shake = async () => {
    const q = question.trim();
    if (!q || phase !== "idle") return;
    abortRef.current?.abort();
    tour.cancel();
    const controller = new AbortController();
    abortRef.current = controller;
    setPhase("shaking");
    setSign(null);
    setAnswer("");
    setError(null);
    setTerm(null);
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let incomplete = false;
    const failReading = () => {
      incomplete = true;
      tour.cancel();
      setAnswer("");
      setTerm(null);
      setError("解签未完整完成，结果可能已保存。请先查看历史记录，再决定是否重试；问题已保留。");
    };
    const { queue, handlers } = tour.begin();
    const playPromise = tour.play(queue, {
      fireCommand: makeQianFireCommand(setTerm),
      onCaption: () => {},
      onReveal: (full) => {
        if (!incomplete) setAnswer(full);
      },
      onTourActiveChange: () => {},
      reducedMotion: reduced,
    });
    try {
      await qianApi.streamOracle(
        { question: q },
        {
          onSign: (s) => {
            setSign(s);
            setPhase("reading");
          },
          onText: handlers.onText,
          onCamera: handlers.onCamera,
          onDone: () => handlers.onDone(0, {}),
          onError: failReading,
        },
        controller.signal,
      );
    } catch (e) {
      failReading();
      if (e instanceof DOMException && e.name === "AbortError") {
        await playPromise;
        setPhase("idle"); // 主动中止后解锁，避免卡在 shaking/reading
        return;
      }
      if (e instanceof QianApiError && e.status === 503)
        setError("解签师未启用（缺少 API Key）");
      else if (e instanceof QianApiError && e.status === 429)
        setError("今日额度已用尽，请明日再来");
      // Network/persistence uncertainty keeps the history-before-retry message.
      await playPromise;
      setPhase("idle");
      return;
    }
    await playPromise;
    setPhase("idle");
  };

  // Split poetry on 。 into lines, re-appending the 。
  const poetryLines = sign?.poetry
    ? sign.poetry
        .split("。")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => s + "。")
    : [];

  return (
    /* ── Outer dark immersive card ─────────────────────────────────────────── */
    <>
    <style>{`@keyframes qianFade{from{opacity:0}to{opacity:1}}`}</style>
    <div
      className="rounded-3xl p-5"
      style={{
        background:
          "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(185,71,47,.22) 0%, #160f08 70%)",
        border: "1px solid #3a2a14",
        borderRadius: "24px",
      }}
    >
      <div className="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">

        {/* ── Left: 3D Scene ─────────────────────────────────────────────────── */}
        <div
          className="relative min-w-0 min-h-[420px] h-[64vh] overflow-hidden"
          style={{
            borderRadius: "18px",
            border: "1px solid rgba(214,168,74,.25)",
          }}
        >
          {/* Gold corner brackets */}
          <span className="pointer-events-none absolute left-2 top-2 h-5 w-5 border-l border-t" style={{ borderColor: "#d6a84a" }} />
          <span className="pointer-events-none absolute right-2 top-2 h-5 w-5 border-r border-t" style={{ borderColor: "#d6a84a" }} />
          <span className="pointer-events-none absolute bottom-2 left-2 h-5 w-5 border-b border-l" style={{ borderColor: "#d6a84a" }} />
          <span className="pointer-events-none absolute bottom-2 right-2 h-5 w-5 border-b border-r" style={{ borderColor: "#d6a84a" }} />

          <QianScene shaking={phase === "shaking"} drawn={!!sign} onRenderError={() => {}} />
          {sign ? (
            <div
              className="pointer-events-none absolute"
              style={{
                left: "50%",
                top: "12%",
                transform: "translateX(-50%)",
                textAlign: "center",
                animation: "qianFade .8s ease both",
              }}
            >
              <div style={{ fontFamily: KAITI, fontSize: "30px", color: "#ffe9c4", textShadow: "0 0 16px rgba(231,195,114,.75)" }}>
                第 {sign.id} 签
              </div>
              <div style={{ fontFamily: KAITI, fontSize: "14px", color: "#e7c372", letterSpacing: "3px", marginTop: "2px" }}>
                {sign.grade} · {sign.palace}
              </div>
            </div>
          ) : null}
          {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
        </div>

        {/* ── Right: Controls + signcard + 解签 ──────────────────────────────── */}
        <div className="flex min-w-0 flex-col gap-4">

          {/* Question textarea */}
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="写下你想问的事，例如「这段时间的事业」……"
            className="resize-none rounded-2xl px-4 py-3 text-sm outline-none focus:outline-none"
            style={{
              background: "#1b130b",
              border: "1px solid rgba(214,168,74,.30)",
              color: "#f4ece0",
              fontFamily: SONGTI,
            }}
          />

          {/* 摇签 button */}
          <button
            type="button"
            onClick={() => void shake()}
            disabled={!question.trim() || phase !== "idle"}
            className="w-full rounded-2xl py-3 text-sm font-bold tracking-[4px] disabled:opacity-40 transition-opacity"
            style={{
              background: "linear-gradient(180deg,#e7c372 0%,#c1872f 100%)",
              color: "#2a1708",
              letterSpacing: "4px",
            }}
          >
            {phase === "idle" ? "摇 签" : phase === "shaking" ? "摇签中…" : "解签中…"}
          </button>

          {/* Error */}
          {error ? (
            <p className="text-xs" role="alert" style={{ color: "#e8794f" }}>
              {error}
            </p>
          ) : null}

          {/* ── Sign card (做旧签纸) ─────────────────────────────────────────── */}
          {sign ? (
            <div
              className="relative rounded-2xl p-4"
              style={{
                background: "linear-gradient(160deg,#efe3c8,#e0cda0)",
                border: "1px solid #d6a84a",
              }}
            >
              {/* 朱砂 seal — top right */}
              <div
                className="absolute right-4 top-4 flex items-center justify-center"
                style={{
                  width: 42,
                  height: 42,
                  background: "#b9472f",
                  borderRadius: 7,
                  transform: "rotate(-6deg)",
                  flexShrink: 0,
                }}
              >
                <span
                  style={{
                    fontFamily: KAITI,
                    fontSize: 20,
                    color: "#f4d9b0",
                    lineHeight: 1,
                  }}
                >
                  灵
                </span>
              </div>

              {/* 吉凶 badge */}
              {(() => {
                const { bg, text } = gradeBadge(sign.grade);
                return (
                  <span
                    className="inline-block rounded px-2 py-0.5 text-xs font-semibold"
                    style={{ background: bg, color: text }}
                  >
                    {sign.grade}
                  </span>
                );
              })()}

              {/* 签号 · palace · title */}
              <p
                className="mt-1.5 text-xs"
                style={{ color: "#7a5a2c", fontFamily: SONGTI }}
              >
                第 {sign.id} 签 · {sign.palace} · {sign.title}
              </p>

              {/* 签诗 divider + poetry */}
              <div
                className="mt-3 pt-3"
                style={{ borderTop: "1px solid rgba(122,58,29,.3)" }}
              >
                {poetryLines.length > 0 ? (
                  poetryLines.map((line, i) => (
                    <p
                      key={i}
                      style={{
                        fontFamily: KAITI,
                        fontSize: 20,
                        lineHeight: 1.7,
                        color: "#3a230f",
                      }}
                    >
                      {line}
                    </p>
                  ))
                ) : (
                  <p
                    className="whitespace-pre-wrap"
                    style={{
                      fontFamily: KAITI,
                      fontSize: 20,
                      lineHeight: 1.7,
                      color: "#3a230f",
                    }}
                  >
                    {sign.poetry}
                  </p>
                )}
              </div>
            </div>
          ) : null}

          {/* ── 解签 glass panel ─────────────────────────────────────────────── */}
          {answer ? (
            <div
              className="rounded-2xl p-4"
              style={{
                background: "rgba(28,18,9,.55)",
                backdropFilter: "blur(8px)",
                WebkitBackdropFilter: "blur(8px)",
                border: "1px solid rgba(214,168,74,.4)",
              }}
            >
              <p
                className="mb-2 text-xs tracking-[4px]"
                style={{ color: "#d6a84a", fontFamily: KAITI }}
              >
                解 签
              </p>
              <p
                className="whitespace-pre-wrap text-sm leading-[1.75]"
                style={{ color: "#e4d7ba", fontFamily: SONGTI }}
              >
                {answer}
              </p>
            </div>
          ) : null}

          {/* ── History 我的灵签 ──────────────────────────────────────────────── */}
          <section className="mt-2 space-y-3" aria-label="我的灵签">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm" style={{ color: "#d6a84a" }}>我的灵签</h2>
              <button type="button" className="rounded border border-amber-200/40 px-3 py-2 text-xs text-amber-100" onClick={() => void refreshHistory()}>刷新历史记录</button>
            </div>
            {historyState === "loading" && <p role="status" className="text-sm text-amber-100">正在读取历史记录…</p>}
            {historyState === "error" && <p role="alert" className="text-sm text-orange-300">历史记录暂不可用，请刷新重试。</p>}
            {historyState === "ready" && history.length === 0 && <p className="text-sm text-amber-100">暂无已保存的灵签记录。</p>}
            <ul className="space-y-2">
              {history.slice(0, expandedHistory ? 50 : 5).map(h => <li key={h.id}>
                <button type="button" aria-label={`查看第${h.sign_id}签记录 ${h.id}`} aria-expanded={selectedId === h.id}
                  className="w-full break-words rounded-xl border border-amber-200/20 px-3 py-2 text-left text-xs"
                  onClick={event => { detailTrigger.current = event.currentTarget; void openDetail(h.id); }}>
                  <span style={{ color: "#d6a84a" }}>第{h.sign_id}签 · {h.grade}</span><MaskedQuestion text={h.question} />
                </button>
              </li>)}
            </ul>
            {history.length > 5 && <button type="button" className="rounded border border-amber-200/40 px-3 py-2 text-xs text-amber-100" onClick={() => setExpandedHistory(value => !value)}>{expandedHistory ? "收起记录" : "展开全部记录"}</button>}
            {selectedId !== null && <section aria-label="灵签历史详情" className="space-y-3 rounded-xl border border-amber-200/30 p-4 text-amber-100">
              <div className="flex flex-wrap justify-between gap-2">
                <h3 ref={detailHeading} tabIndex={-1} className="font-medium">已保存的解签内容</h3>
                <button type="button" className="rounded border border-amber-200/40 px-3 py-2 text-xs" onClick={closeDetail}>关闭详情</button>
              </div>
              <p className="text-xs">这里只展示已保存内容，可能包含中断时保存的部分结果；不代表解签完整完成，也不代表付款状态。不会自动播放或重新解签。</p>
              {detailState === "loading" && <p role="status">读取历史详情中…</p>}
              {detailState === "error" && <div><p role="alert">{detailError}</p><button type="button" className="mt-2 rounded border border-amber-200/40 px-3 py-2" onClick={() => void openDetail(selectedId)}>重试读取详情</button></div>}
              {detailState === "ready" && detail && <>
                <p className="text-sm">第{detail.sign_id}签 · {detail.grade}</p>
                <p className="whitespace-pre-wrap break-words text-sm">{detail.question}</p>
                <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{detail.response}</p>
                {detail.created_at && <p className="break-words text-xs">保存时间：{detail.created_at}</p>}
              </>}
            </section>}
          </section>
        </div>
      </div>
    </div>
    </>
  );
}
