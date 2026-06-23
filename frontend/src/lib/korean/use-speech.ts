"use client";
import { useCallback, useRef, useState } from "react";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

function getRecognition(): SpeechRecognitionLike | null {
  if (typeof window === "undefined") return null;
  const Ctor =
    (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionLike }).webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

/** Browser Web Speech API (ko-KR). `supported` is false on Safari/Firefox — callers hide the mic. */
export function useSpeech() {
  const [supported] = useState<boolean>(() => getRecognition() !== null);
  const [listening, setListening] = useState(false);
  const recRef = useRef<SpeechRecognitionLike | null>(null);

  const listen = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      const rec = getRecognition();
      if (!rec) {
        resolve("");
        return;
      }
      recRef.current = rec;
      rec.lang = "ko-KR";
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      let result = "";
      rec.onresult = (e) => {
        result = e.results?.[0]?.[0]?.transcript ?? "";
      };
      rec.onerror = () => {
        setListening(false);
        resolve("");
      };
      rec.onend = () => {
        setListening(false);
        resolve(result);
      };
      setListening(true);
      rec.start();
    });
  }, []);

  const stop = useCallback(() => recRef.current?.stop(), []);

  return { supported, listening, listen, stop };
}

/** Normalize + fuzzy-compare for scene-line "judges meaning" check (no AI call). */
export function matchesIntent(transcript: string, accepted: { ko: string }[]): boolean {
  const norm = (s: string) => s.replace(/\s+/g, "").replace(/[.,!?]/g, "");
  const t = norm(transcript);
  if (!t) return false;
  return accepted.some((a) => {
    const target = norm(a.ko);
    return t.includes(target) || target.includes(t);
  });
}
