"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { qianApi, QianApiError, type QianSign, type QianReadingOut } from "@/lib/qian/api";
import { useOracleTour } from "@/components/ziwei/chat-dock/use-oracle-tour";
import { TermCard, type TermInfo } from "@/components/ziwei/term-card";
import { makeQianFireCommand } from "./qian-camera";

// ── Font stacks ────────────────────────────────────────────────────────────────
const KAITI = "'STKaiti','KaiTi STD','KaiTi','楷体','Kaiti SC',serif";
const SONGTI = "'Songti SC','Noto Serif CJK SC','SimSun',serif";

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
  const abortRef = useRef<AbortController | null>(null);
  const tour = useOracleTour();

  // 仅卸载时中止在途流 + 停指挥器。依赖稳定的 cancel（useOracleTour 每次渲染返回新对象字面量，
  // 用 [tour] 会让 cleanup 每次渲染都触发、把刚发起的流误中止）。cancel 是 useCallback 稳定引用。
  const { cancel: cancelTour } = tour;
  useEffect(() => () => { abortRef.current?.abort(); cancelTour(); }, [cancelTour]);

  useEffect(() => {
    if (phase === "idle") qianApi.listReadings().then(setHistory).catch(() => {});
  }, [phase]);

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
    const { queue, handlers } = tour.begin();
    const playPromise = tour.play(queue, {
      fireCommand: makeQianFireCommand(setTerm),
      onCaption: () => {},
      onReveal: (full) => {
        setAnswer(full);
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
          onError: handlers.onError,
        },
        controller.signal,
      );
    } catch (e) {
      tour.cancel();
      if (e instanceof DOMException && e.name === "AbortError") {
        await playPromise;
        setPhase("idle"); // 主动中止后解锁，避免卡在 shaking/reading
        return;
      }
      if (e instanceof QianApiError && e.status === 503)
        setError("解签师未启用（缺少 API Key）");
      else if (e instanceof QianApiError && e.status === 429)
        setError("今日额度已用尽，请明日再来");
      else setError("解签暂不可用，请稍后再试");
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
      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">

        {/* ── Left: 3D Scene ─────────────────────────────────────────────────── */}
        <div
          className="relative min-h-[420px] h-[64vh] overflow-hidden"
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
        <div className="flex flex-col gap-4">

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
          {history.length > 0 ? (
            <div className="mt-2">
              <p
                className="text-xs uppercase tracking-[0.2em]"
                style={{ color: "rgba(214,168,74,.6)" }}
              >
                我的灵签
              </p>
              <div className="mt-2 space-y-1.5">
                {history.slice(0, 5).map((h) => (
                  <div
                    key={h.id}
                    className="rounded-xl px-3 py-2 text-xs"
                    style={{
                      background: "rgba(28,18,9,.4)",
                      border: "1px solid rgba(214,168,74,.15)",
                    }}
                  >
                    <span style={{ color: "#d6a84a" }}>
                      第{h.sign_id}签 · {h.grade}
                    </span>
                    <span className="ml-2" style={{ color: "rgba(233,220,196,.7)" }}>
                      {h.question}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
    </>
  );
}
