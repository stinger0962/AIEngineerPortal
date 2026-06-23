"use client";

import { useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import { useSpeech, matchesIntent } from "@/lib/korean/use-speech";
import { useRomaji } from "./romanization-toggle";
import { PrimaryButton, SectionLabel } from "./ui";
import type { SceneContent } from "@/lib/korean/types";

const SCENE = "#b9532b"; // 적 persimmon

function SpeakIcon({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} aria-label="play" className="k-press text-[var(--celadon-600)] hover:text-[var(--celadon-700)]">
      <svg viewBox="0 0 24 24" className="h-4 w-4">
        <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
        <path d="M16 8c1.5 1.2 1.5 6.8 0 8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </button>
  );
}

export function SceneNode({ content, onDone }: { content: SceneContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const { supported, listening, listen } = useSpeech();
  const [romajiOn, setRomajiOn] = useRomaji();
  const [turnIdx, setTurnIdx] = useState(0);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  const turn = content.your_turns[turnIdx];
  const done = turnIdx >= content.your_turns.length;

  const advance = () => {
    setFeedback(null);
    setTurnIdx((i) => i + 1);
  };
  const tryAnswer = (text: string) => {
    if (matchesIntent(text, turn.accepted) || turn.options.includes(text)) {
      setFeedback({ ok: true, text: "좋아요! ✓" });
      setTimeout(advance, 650);
    } else {
      setFeedback({ ok: false, text: "다시 한 번 — try again, or tap an option." });
    }
  };
  const onMic = async () => {
    const heard = await listen();
    if (heard) tryAnswer(heard);
  };

  return (
    <div className="space-y-5">
      {/* romanization toggle */}
      <div className="flex justify-end">
        <button
          onClick={() => setRomajiOn(!romajiOn)}
          className="k-press inline-flex items-center gap-2 rounded-full border border-ink/12 bg-white/55 px-3 py-1.5 text-xs text-ink/60"
        >
          <span className={`relative h-3.5 w-6 rounded-full transition-colors ${romajiOn ? "bg-[var(--celadon-500)]" : "bg-ink/15"}`}>
            <span className={`absolute top-0.5 h-2.5 w-2.5 rounded-full bg-white transition-all ${romajiOn ? "left-3" : "left-0.5"}`} />
          </span>
          romanization
        </button>
      </div>

      {/* dialogue */}
      <div className="space-y-2.5">
        {content.lines.map((line, i) => {
          const you = line.speaker === "you";
          return (
            <div key={i} className={`flex ${you ? "justify-end" : "justify-start"}`}>
              <div
                className={`k-card max-w-[85%] rounded-2xl px-4 py-2.5 ${you ? "rounded-br-md" : "rounded-bl-md"}`}
                style={you ? { background: "linear-gradient(180deg,#eef5f1,#ffffff)" } : undefined}
              >
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="font-kr text-[11px] uppercase tracking-[0.16em] text-ink/40">{line.speaker}</span>
                  <SpeakIcon onClick={() => speak(line.ko)} />
                </div>
                <p className="font-kr-serif text-lg text-ink">{line.ko}</p>
                {romajiOn && (
                  <p className="font-kr mt-0.5 text-xs italic text-ink/45">
                    {line.romaji} — {line.en}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* your turn / complete */}
      {!done ? (
        <div className="k-card rounded-2xl p-4" style={{ borderColor: "rgba(185,83,43,0.32)" }}>
          <SectionLabel>당신 차례 · Your line</SectionLabel>
          <p className="mb-3 mt-1 text-sm text-ink/70">{turn.prompt_en}</p>
          <div className="flex flex-wrap gap-2">
            {turn.options.map((o) => (
              <button
                key={o}
                onClick={() => tryAnswer(o)}
                className="k-card k-press font-kr-serif rounded-xl px-4 py-2 text-lg text-ink transition-transform hover:-translate-y-0.5"
              >
                {o}
              </button>
            ))}
          </div>
          {supported && (
            <button
              onClick={onMic}
              className="k-press mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-white"
              style={{ background: listening ? "linear-gradient(180deg,#d98a4e,#b9532b)" : "linear-gradient(180deg,#cf7142,#b9532b)" }}
            >
              🎤 {listening ? "듣는 중… Listening" : "말해 보기 · Say it"}
            </button>
          )}
          {feedback && (
            <p className="mt-3 text-sm font-medium" style={{ color: feedback.ok ? "var(--celadon-700)" : SCENE }}>
              {feedback.text}
            </p>
          )}
        </div>
      ) : (
        <PrimaryButton onClick={() => onDone(3)}>장면 완료 · Scene complete ✓</PrimaryButton>
      )}
    </div>
  );
}
