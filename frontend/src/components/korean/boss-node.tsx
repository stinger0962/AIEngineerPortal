"use client";

import { useRef, useState } from "react";
import { koreanApi } from "@/lib/korean/api";
import { useSpeech } from "@/lib/korean/use-speech";
import { useTts } from "@/lib/korean/use-tts";
import type { BossContent } from "@/lib/korean/types";
import { PrimaryButton, Stars } from "./ui";

type Msg = { role: "user" | "assistant"; content: string };
const BOSS = "var(--kr-boss)";

function TypingDots() {
  return (
    <div className="flex items-center gap-1 pl-1 text-ink/40">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:300ms]" />
    </div>
  );
}

export function BossNode({
  slug,
  content,
  onDone,
}: {
  slug: string;
  content: BossContent;
  onDone: (stars: number) => void;
}) {
  const { speak } = useTts();
  const { supported, listening, listen } = useSpeech();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [won, setWon] = useState(false);
  const convId = useRef<number | undefined>(undefined);

  const send = async (text: string) => {
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    let reply = "";
    await koreanApi.streamBoss(
      slug,
      { message: text, conversation_id: convId.current },
      {
        onText: (delta) => {
          reply += delta;
        },
        onDone: (cid, goalMet) => {
          convId.current = cid;
          if (reply) {
            setMessages((m) => [...m, { role: "assistant", content: reply }]);
            speak(reply);
          }
          if (goalMet) setWon(true);
          setBusy(false);
        },
        onError: () => {
          setMessages((m) => [...m, { role: "assistant", content: "(연결 오류 — 다시 시도하세요)" }]);
          setBusy(false);
        },
      },
    );
  };

  const onMic = async () => {
    const heard = await listen();
    if (heard) send(heard);
  };

  return (
    <div className="space-y-4">
      {/* goal */}
      <div className="k-card flex items-center gap-3 rounded-2xl px-4 py-3" style={{ borderColor: "rgba(54,64,122,0.3)" }}>
        <span className="font-kr-serif flex h-9 w-9 items-center justify-center rounded-full text-white" style={{ background: BOSS }}>
          왕
        </span>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: BOSS }}>
            목표 · Goal
          </p>
          <p className="text-sm text-ink/80">{content.goal_en}</p>
        </div>
      </div>

      {/* chat */}
      <div className="k-card min-h-[210px] space-y-2.5 rounded-2xl p-4">
        {messages.length === 0 && !busy && (
          <p className="font-kr text-sm text-ink/40">인사로 시작해 보세요 — say hello to begin.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <span
              className={`max-w-[82%] rounded-2xl px-3.5 py-2 text-[15px] ${
                m.role === "user" ? "rounded-br-md text-white" : "k-card rounded-bl-md font-kr-serif text-ink"
              }`}
              style={m.role === "user" ? { background: "linear-gradient(180deg,var(--celadon-500),var(--celadon-600))" } : undefined}
            >
              {m.content}
            </span>
          </div>
        ))}
        {busy && <TypingDots />}
      </div>

      {won ? (
        <div className="k-card k-pop rounded-2xl p-5 text-center">
          <p className="font-kr-serif text-xl text-ink">통과! Goal cleared</p>
          <div className="mt-2 flex justify-center">
            <Stars value={3} />
          </div>
          <div className="mt-4">
            <PrimaryButton tone="gold" onClick={() => onDone(3)}>
              별 받기 · Claim ★★★
            </PrimaryButton>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex flex-1 gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
              className="font-kr-serif flex-1 rounded-2xl border border-ink/12 bg-white/70 px-4 py-2.5 text-ink outline-none focus:border-[var(--celadon-500)] disabled:opacity-60"
              placeholder="한국어로 말해보세요…"
            />
            <PrimaryButton type="submit" disabled={busy}>
              보내기
            </PrimaryButton>
          </form>
          {supported && (
            <button
              onClick={onMic}
              disabled={busy}
              aria-label="speak"
              className="k-press rounded-2xl px-4 text-lg text-white disabled:opacity-50"
              style={{ background: listening ? "#4a57a0" : BOSS }}
            >
              🎤
            </button>
          )}
        </div>
      )}
    </div>
  );
}
