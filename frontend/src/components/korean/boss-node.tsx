"use client";
import { useRef, useState } from "react";
import { koreanApi } from "@/lib/korean/api";
import { useSpeech } from "@/lib/korean/use-speech";
import { useTts } from "@/lib/korean/use-tts";
import type { BossContent } from "@/lib/korean/types";

type Msg = { role: "user" | "assistant"; content: string };

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
      <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/5 p-3 text-sm">
        🎯 Goal: {content.goal_en}
      </div>
      <div className="min-h-[180px] space-y-2 rounded-xl bg-white/5 p-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={`inline-block rounded-xl px-3 py-1.5 text-sm ${
                m.role === "user" ? "bg-emerald-400/20" : "bg-white/10"
              }`}
            >
              {m.content}
            </span>
          </div>
        ))}
        {busy && <div className="text-xs opacity-50">…</div>}
      </div>

      {won ? (
        <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
          Goal cleared — claim ★★★
        </button>
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
              className="flex-1 rounded-lg border border-white/15 bg-transparent px-3 py-2"
              placeholder="한국어로 말해보세요…"
            />
            <button disabled={busy} className="rounded-lg bg-emerald-400/30 px-4 py-2">
              Send
            </button>
          </form>
          {supported && (
            <button
              onClick={onMic}
              disabled={busy}
              className={`rounded-lg px-4 py-2 ${listening ? "bg-amber-500/40" : "bg-amber-500/20 hover:bg-amber-500/30"}`}
            >
              🎤
            </button>
          )}
        </div>
      )}
    </div>
  );
}
