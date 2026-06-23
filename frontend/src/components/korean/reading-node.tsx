"use client";

import { useTts } from "@/lib/korean/use-tts";
import type { ReadingContent } from "@/lib/korean/types";
import { PrimaryButton, SectionLabel, SpeakTile } from "./ui";

const A = "var(--kr-reading)";

export function ReadingNode({ content, onDone }: { content: ReadingContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();

  return (
    <div className="space-y-7">
      <section className="space-y-3">
        <SectionLabel>자모 · Letters — tap to hear</SectionLabel>
        <div className="flex flex-wrap gap-2.5">
          {content.letters.map((l) => (
            <SpeakTile
              key={l.audio_key}
              ko={l.jamo}
              sub={l.sound}
              onSpeak={() => speak(l.jamo)}
              accent={A}
              className="min-w-[80px]"
              koClassName="text-3xl"
            />
          ))}
        </div>
      </section>

      {content.blocks.length > 0 && (
        <section className="space-y-3">
          <SectionLabel>글자 만들기 · Build syllable blocks</SectionLabel>
          <div className="flex flex-wrap gap-2.5">
            {content.blocks.map((b) => (
              <SpeakTile
                key={b.ko}
                ko={b.ko}
                sub={b.romaji}
                onSpeak={() => speak(b.ko)}
                accent={A}
                className="min-w-[88px]"
                koClassName="text-3xl"
              />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <SectionLabel>읽어 보기 · Read these words</SectionLabel>
        <div className="flex flex-wrap gap-2.5">
          {content.words.map((w) => (
            <SpeakTile key={w.ko} ko={w.ko} sub={w.en} onSpeak={() => speak(w.ko)} accent={A} koClassName="text-2xl" />
          ))}
        </div>
      </section>

      <div className="pt-1">
        <PrimaryButton onClick={() => onDone(3)}>다 읽었어요 · I can read these ✓</PrimaryButton>
      </div>
    </div>
  );
}
