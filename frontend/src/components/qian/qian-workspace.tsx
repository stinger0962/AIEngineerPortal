"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { qianApi, QianApiError, type QianSign, type QianReadingOut } from "@/lib/qian/api";
import { useOracleTour } from "@/components/ziwei/chat-dock/use-oracle-tour";
import { TermCard, type TermInfo } from "@/components/ziwei/term-card";
import { makeQianFireCommand } from "./qian-camera";

const QianScene = dynamic(() => import("./scene3d/qian-scene"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] items-center justify-center">
      <p className="animate-pulse text-sm text-[#d6a84a]/70">正在备好签筒……</p>
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

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="relative overflow-hidden rounded-[28px] border border-[#d6a84a]/20 bg-[#140e08] min-h-[420px] h-[64vh]">
        <QianScene shaking={phase === "shaking"} drawn={!!sign} onRenderError={() => {}} />
        {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
      </div>
      <div className="flex flex-col gap-4">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          placeholder="写下你想问的事，例如「这段时间的事业」……"
          className="resize-none rounded-2xl border border-[#d6a84a]/30 bg-[#1b130b] px-4 py-3 text-sm text-[#f4ece0] placeholder-[#d6a84a]/40 outline-none focus:border-[#d6a84a]/60"
        />
        <button
          type="button"
          onClick={() => void shake()}
          disabled={!question.trim() || phase !== "idle"}
          className="rounded-2xl bg-gradient-to-br from-[#d6a84a] to-[#b9472f] px-4 py-3 text-sm font-semibold text-[#140e08] disabled:opacity-40"
        >
          {phase === "idle" ? "摇 签" : phase === "shaking" ? "摇签中…" : "解签中…"}
        </button>
        {error ? (
          <p className="text-xs text-[#e8794f]" role="alert">
            {error}
          </p>
        ) : null}
        {sign ? (
          <div className="rounded-2xl border border-[#d6a84a]/25 bg-[#1b130b] p-4">
            <p className="text-xs text-[#d6a84a]">
              第 {sign.id} 签 · {sign.grade} · {sign.palace}
            </p>
            <p className="mt-1 text-sm font-semibold text-[#f4ece0]">{sign.title}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#e9dcc4]">
              {sign.poetry}
            </p>
          </div>
        ) : null}
        {answer ? (
          <div className="whitespace-pre-wrap rounded-2xl border border-[#d6a84a]/15 bg-[#1b130b]/60 p-4 text-sm leading-relaxed text-[#f4ece0]">
            {answer}
          </div>
        ) : null}
        {history.length > 0 ? (
          <div className="mt-2">
            <p className="text-xs uppercase tracking-[0.2em] text-[#d6a84a]/60">我的灵签</p>
            <div className="mt-2 space-y-1.5">
              {history.slice(0, 5).map((h) => (
                <div key={h.id} className="rounded-xl border border-[#d6a84a]/15 bg-[#1b130b]/50 px-3 py-2 text-xs text-[#e9dcc4]/80">
                  <span className="text-[#d6a84a]">第{h.sign_id}签 · {h.grade}</span>
                  <span className="ml-2 text-[#e9dcc4]/60">{h.question}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
