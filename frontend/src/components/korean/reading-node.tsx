"use client";
import { useTts } from "@/lib/korean/use-tts";
import type { ReadingContent } from "@/lib/korean/types";

export function ReadingNode({ content, onDone }: { content: ReadingContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm uppercase opacity-60">Letters — tap to hear</h3>
        <div className="flex flex-wrap gap-2">
          {content.letters.map((l) => (
            <button
              key={l.jamo}
              onClick={() => speak(l.jamo)}
              className="rounded-lg border border-white/15 px-4 py-3 text-2xl hover:bg-white/10"
            >
              {l.jamo}
              <span className="ml-1 text-xs opacity-50">{l.sound}</span>
            </button>
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-2 text-sm uppercase opacity-60">Read these words</h3>
        <div className="flex flex-wrap gap-3">
          {content.words.map((w) => (
            <button key={w.ko} onClick={() => speak(w.ko)} className="rounded-lg bg-white/5 px-4 py-2 hover:bg-white/10">
              <span className="text-lg">{w.ko}</span>
              <span className="ml-2 text-xs opacity-60">{w.en}</span>
            </button>
          ))}
        </div>
      </section>
      <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
        I can read these ✓
      </button>
    </div>
  );
}
