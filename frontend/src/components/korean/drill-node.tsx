"use client";
import { useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import type { DrillContent, DrillItem } from "@/lib/korean/types";

function choicesFor(item: DrillItem): string[] {
  if (item.type === "match" || item.type === "listen") return item.choices;
  return [];
}

export function DrillNode({ content, onDone }: { content: DrillContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const [idx, setIdx] = useState(0);
  const [typed, setTyped] = useState("");
  const [wrong, setWrong] = useState(0);
  const item = content.items[idx];
  const finished = idx >= content.items.length;

  const submit = (value: string) => {
    if (value.replace(/\s+/g, "") === item.answer.replace(/\s+/g, "")) {
      setTyped("");
      setIdx(idx + 1);
    } else {
      setWrong(wrong + 1);
    }
  };

  if (finished) {
    const stars = wrong === 0 ? 3 : wrong <= 2 ? 2 : 1;
    return (
      <button onClick={() => onDone(stars)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
        Drill complete — {"★".repeat(stars)} ✓
      </button>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-sky-400/40 p-4">
      <div className="text-xs uppercase opacity-60">
        {idx + 1} / {content.items.length}
      </div>
      {item.type === "match" && <div className="text-2xl">{item.ko}</div>}
      {item.type === "listen" && (
        <button onClick={() => speak(item.answer)} className="rounded-lg bg-white/10 px-4 py-2">🔊 Listen</button>
      )}
      {item.type === "fill" && <div className="text-lg">{item.prompt}</div>}
      {item.type === "type" && <div className="text-lg">{item.prompt_en}</div>}

      {choicesFor(item).length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {choicesFor(item).map((c) => (
            <button key={c} onClick={() => submit(c)} className="rounded-lg bg-sky-400/20 px-4 py-2 hover:bg-sky-400/30">
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
            className="flex-1 rounded-lg border border-white/15 bg-transparent px-3 py-2"
            placeholder="Type 한글…"
          />
          <button className="rounded-lg bg-sky-400/30 px-4 py-2">Check</button>
        </form>
      )}
    </div>
  );
}
