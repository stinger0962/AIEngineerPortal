"use client";

import { useEffect, useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import type { DrillContent, DrillItem } from "@/lib/korean/types";
import { PrimaryButton, SectionLabel, Stars } from "./ui";
import { Mascot, MascotCoach, useMascot } from "./mascot";

const A = "var(--kr-drill)";

function choicesFor(item: DrillItem): string[] {
  if (item.type === "match" || item.type === "listen") return item.choices;
  return [];
}

export function DrillNode({ content, onDone }: { content: DrillContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const [idx, setIdx] = useState(0);
  const [typed, setTyped] = useState("");
  const [wrong, setWrong] = useState(0);
  const [miss, setMiss] = useState(false);
  const m = useMascot();
  const item = content.items[idx];
  const finished = idx >= content.items.length;

  useEffect(() => {
    m.say("뜻을 맞혀 보세요!");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = (value: string) => {
    if (value.replace(/\s+/g, "") === item.answer.replace(/\s+/g, "")) {
      m.correct();
      setTyped("");
      setMiss(false);
      setIdx(idx + 1);
    } else {
      m.wrong();
      setWrong((w) => w + 1);
      setMiss(true);
      window.setTimeout(() => setMiss(false), 500);
    }
  };

  if (finished) {
    const stars = wrong === 0 ? 3 : wrong <= 2 ? 2 : 1;
    return (
      <div className="k-card k-pop rounded-3xl p-7 text-center">
        <div className="mb-1 flex justify-center">
          <Mascot mood="cheer" size={94} />
        </div>
        <p className="font-kr-serif text-2xl text-ink">잘했어요!</p>
        <p className="mt-1 text-sm text-ink/55">Drill complete</p>
        <div className="mt-3 flex justify-center">
          <Stars value={stars} />
        </div>
        <div className="mt-5">
          <PrimaryButton onClick={() => onDone(stars)}>지도로 · Back to map ✓</PrimaryButton>
        </div>
      </div>
    );
  }

  const choices = choicesFor(item);
  return (
    <div className="space-y-5">
      <MascotCoach mood={m.mood} bubble={m.bubble} size={60} />

      {/* progress */}
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink/8">
          <div
            className="h-full rounded-full transition-[width] duration-300"
            style={{ width: `${(idx / content.items.length) * 100}%`, background: A }}
          />
        </div>
        <span className="text-xs text-ink/45">
          {idx + 1} / {content.items.length}
        </span>
      </div>

      <div className={`k-card rounded-3xl p-6 ${miss ? "k-pop" : ""}`} style={miss ? { borderColor: "#b9532b" } : undefined}>
        <SectionLabel>연습 · Drill</SectionLabel>
        <div className="mb-4 mt-3 min-h-[56px]">
          {item.type === "match" && <p className="font-kr-serif text-4xl text-ink">{item.ko}</p>}
          {item.type === "listen" && (
            <button
              onClick={() => speak(item.answer)}
              className="k-press inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-white"
              style={{ background: "linear-gradient(180deg,var(--celadon-500),var(--celadon-600))" }}
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5">
                <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
                <path d="M16 8c1.5 1.2 1.5 6.8 0 8M18.5 6c2.8 2 2.8 10 0 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              들어보기 · Listen
            </button>
          )}
          {item.type === "fill" && <p className="font-kr-serif text-2xl text-ink">{item.prompt}</p>}
          {item.type === "type" && <p className="text-lg text-ink/80">{item.prompt_en}</p>}
        </div>

        {choices.length > 0 ? (
          <div className="flex flex-wrap gap-2.5">
            {choices.map((c) => (
              <button
                key={c}
                onClick={() => submit(c)}
                className="k-card k-press font-kr-serif rounded-xl px-4 py-2.5 text-lg text-ink transition-transform hover:-translate-y-0.5"
              >
                {c}
              </button>
            ))}
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(typed);
            }}
            className="flex gap-2"
          >
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              className="font-kr-serif flex-1 rounded-xl border border-ink/12 bg-white/70 px-4 py-2.5 text-lg text-ink outline-none focus:border-[var(--celadon-500)]"
              placeholder="한글 입력…"
            />
            <PrimaryButton type="submit">확인</PrimaryButton>
          </form>
        )}
      </div>
    </div>
  );
}
