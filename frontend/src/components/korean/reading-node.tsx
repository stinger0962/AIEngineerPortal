"use client";

import { useTts } from "@/lib/korean/use-tts";
import type { ReadingContent } from "@/lib/korean/types";
import { PrimaryButton, SectionLabel, SpeakTile } from "./ui";
import { Mascot } from "./mascot";

function Stagger({ children }: { children: React.ReactNode[] }) {
  return (
    <div className="flex flex-wrap gap-3">
      {children.map((c, i) => (
        <div key={i} className="k-bounce-in" style={{ animationDelay: `${Math.min(i, 10) * 45}ms` }}>
          {c}
        </div>
      ))}
    </div>
  );
}

export function ReadingNode({ content, onDone }: { content: ReadingContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <SectionLabel>자모 · Letters — tap to hear</SectionLabel>
        <Stagger>
          {content.letters.map((l) => (
            <SpeakTile key={l.audio_key} ko={l.jamo} sub={l.sound} onSpeak={() => speak(l.jamo)} glaze="celadon" koClassName="text-4xl" />
          ))}
        </Stagger>
      </section>

      {content.blocks.length > 0 && (
        <section className="space-y-3">
          <SectionLabel>글자 만들기 · Build syllable blocks</SectionLabel>
          <Stagger>
            {content.blocks.map((b) => (
              <SpeakTile key={b.ko} ko={b.ko} sub={b.romaji} onSpeak={() => speak(b.ko)} glaze="warm" koClassName="text-4xl" className="min-w-[92px]" />
            ))}
          </Stagger>
        </section>
      )}

      <section className="space-y-3">
        <SectionLabel>읽어 보기 · Read these words</SectionLabel>
        <Stagger>
          {content.words.map((w) => (
            <SpeakTile key={w.ko} ko={w.ko} sub={w.en} onSpeak={() => speak(w.ko)} glaze="clay" koClassName="text-3xl" className="min-w-[120px]" />
          ))}
        </Stagger>
      </section>

      {/* finish — mascot cheers you on */}
      <div className="flex items-center gap-4 pt-2">
        <Mascot size={68} />
        <div>
          <p className="font-kr-serif text-lg text-ink">다 읽었나요?</p>
          <p className="font-kr mb-2 text-xs text-ink/50">Tap each one, then claim your stars.</p>
          <PrimaryButton onClick={() => onDone(3)}>다 읽었어요 · I can read these ✓</PrimaryButton>
        </div>
      </div>
    </div>
  );
}
