"use client";
import { useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import { useSpeech, matchesIntent } from "@/lib/korean/use-speech";
import { useRomaji, RomanizationToggle } from "./romanization-toggle";
import type { SceneContent } from "@/lib/korean/types";

export function SceneNode({ content, onDone }: { content: SceneContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const { supported, listening, listen } = useSpeech();
  const [romajiOn, setRomajiOn] = useRomaji();
  const [turnIdx, setTurnIdx] = useState(0);
  const [feedback, setFeedback] = useState<string>("");

  const turn = content.your_turns[turnIdx];
  const done = turnIdx >= content.your_turns.length;

  const advance = () => {
    setFeedback("");
    setTurnIdx((i) => i + 1);
  };

  const tryAnswer = (text: string) => {
    if (matchesIntent(text, turn.accepted) || turn.options.includes(text)) {
      setFeedback("좋아요! ✓");
      setTimeout(advance, 600);
    } else {
      setFeedback("Not quite — try again or tap an option.");
    }
  };

  const onMic = async () => {
    const heard = await listen();
    if (heard) tryAnswer(heard);
  };

  return (
    <div className="space-y-5">
      <RomanizationToggle on={romajiOn} onChange={setRomajiOn} />
      <div className="space-y-3">
        {content.lines.map((line, i) => (
          <div key={i} className="rounded-xl bg-white/5 p-3">
            <div className="text-xs opacity-50">{line.speaker}</div>
            <div className="flex items-center gap-2">
              <span className="text-lg">{line.ko}</span>
              <button onClick={() => speak(line.ko)} className="text-sm opacity-60 hover:opacity-100">🔊</button>
            </div>
            {romajiOn && <div className="text-xs italic opacity-50">{line.romaji} — {line.en}</div>}
          </div>
        ))}
      </div>

      {!done ? (
        <div className="space-y-3 rounded-xl border border-violet-400/40 p-4">
          <div className="text-xs uppercase opacity-60">Your line — {turn.prompt_en}</div>
          <div className="flex flex-wrap gap-2">
            {turn.options.map((o) => (
              <button key={o} onClick={() => tryAnswer(o)} className="rounded-lg bg-violet-400/20 px-4 py-2 hover:bg-violet-400/30">
                {o}
              </button>
            ))}
          </div>
          {supported && (
            <button
              onClick={onMic}
              className={`rounded-lg px-4 py-2 ${listening ? "bg-amber-500/40" : "bg-amber-500/20 hover:bg-amber-500/30"}`}
            >
              🎤 {listening ? "Listening…" : "Say it"}
            </button>
          )}
          {feedback && <div className="text-sm opacity-80">{feedback}</div>}
        </div>
      ) : (
        <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
          Scene complete ✓
        </button>
      )}
    </div>
  );
}
