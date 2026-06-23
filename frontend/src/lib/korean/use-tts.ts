"use client";
import { useCallback, useRef } from "react";
import { koreanApi } from "./api";

/** Fetches Korean TTS audio, caches blob URLs by text, plays it. Silent no-op on failure
 * (TTS is an enhancement, never a gate). */
export function useTts() {
  const cache = useRef<Map<string, string>>(new Map());

  const speak = useCallback(async (text: string) => {
    if (!text) return;
    try {
      let url = cache.current.get(text);
      if (!url) {
        const res = await fetch(koreanApi.ttsUrl(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (!res.ok) return;
        const blob = await res.blob();
        url = URL.createObjectURL(blob);
        cache.current.set(text, url);
      }
      await new Audio(url).play();
    } catch {
      // swallow — audio is optional
    }
  }, []);

  return { speak };
}
