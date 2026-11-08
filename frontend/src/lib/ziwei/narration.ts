// frontend/src/lib/ziwei/narration.ts

import { paidProduct } from "@/lib/product/config";
import { paidRequestHeaders, paidRequestOptions, invalidatePaidSession } from "@/lib/product/account";
import { API_BASE } from "@/lib/api";
import { stripMarkdown } from "./text";

/** 一段解说的播放源：speak 在朗读结束（或定时结束）时 resolve；cancel 立即停止。
 * V1 用浏览器 SpeechSynthesis；V2 只需新增 CloudNarration，指挥器与 UI 不变。 */
export interface NarrationSource {
  speak(text: string): Promise<void>;
  cancel(): void;
}

/** 估算朗读时长（静音/无语音时给指挥器一个节拍时钟）。 */
export function estimateDuration(text: string): number {
  const ms = text.length * 180;
  return Math.min(Math.max(ms, 800), 12000);
}

/** 浏览器内置语音（默认方案）。挑 zh-CN 嗓音，语速略慢契合解盘调性。 */
export class BrowserNarration implements NarrationSource {
  private current: SpeechSynthesisUtterance | null = null;
  private resolveFn: (() => void) | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;

  static isSupported(): boolean {
    return typeof window !== "undefined" && !!window.speechSynthesis
      && typeof window.speechSynthesis.speak === "function"
      && typeof SpeechSynthesisUtterance !== "undefined";
  }

  private pickVoice(): SpeechSynthesisVoice | null {
    let voices: SpeechSynthesisVoice[];
    try { voices = window.speechSynthesis.getVoices(); } catch { return null; }
    return (
      voices.find((v) => v.lang === "zh-CN") ??
      voices.find((v) => v.lang?.toLowerCase().startsWith("zh")) ??
      null
    );
  }

  speak(text: string): Promise<void> {
    this.cancel();
    const spoken = stripMarkdown(text);
    if (!BrowserNarration.isSupported() || !spoken.trim()) return Promise.resolve();
    return new Promise<void>((resolve) => {
      let u: SpeechSynthesisUtterance;
      try { u = new SpeechSynthesisUtterance(spoken); } catch { resolve(); return; }
      u.lang = "zh-CN";
      u.rate = 0.92;
      const voice = this.pickVoice();
      if (voice) u.voice = voice;
      let settled = false;
      const settle = () => {
        if (settled) return;
        settled = true;
        u.onend = null; u.onerror = null;
        if (this.current === u) {
          if (this.timer) clearTimeout(this.timer);
          this.timer = null; this.current = null; this.resolveFn = null;
        }
        resolve();
      };
      u.onend = settle;
      u.onerror = settle;
      this.current = u;
      this.resolveFn = settle;
      this.timer = setTimeout(() => { settle(); try { window.speechSynthesis.cancel(); } catch { /* Deadline still settles. */ } }, 30000);
      try { window.speechSynthesis.speak(u); } catch { settle(); }
    });
  }

  cancel(): void {
    const r = this.resolveFn;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.current) { this.current.onend = null; this.current.onerror = null; }
    this.current = null;
    this.resolveFn = null;
    if (BrowserNarration.isSupported()) {
      try { window.speechSynthesis.cancel(); } catch { /* Always settle our promise even if the browser fails. */ }
    }
    r?.(); // 主动 resolve 在途 Promise——不依赖浏览器是否补发 onend/onerror（Safari 可能都不发）
  }
}

/** 静音/不支持时用：按估算时长定时，让画面编排照常有节拍。 */
export class SilentNarration implements NarrationSource {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private resolveFn: (() => void) | null = null;

  speak(text: string): Promise<void> {
    this.cancel();
    if (!text.trim()) return Promise.resolve();
    return new Promise<void>((resolve) => {
      this.resolveFn = resolve;
      this.timer = setTimeout(() => {
        this.timer = null;
        this.resolveFn = null;
        resolve();
      }, estimateDuration(text));
    });
  }

  cancel(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const r = this.resolveFn;
    this.resolveFn = null;
    r?.();
  }
}

/** Cloud narration is best-effort: bounded network/playback, no automatic
 * provider retry, and browser fallback except on expired paid authentication. */
export class CloudNarration implements NarrationSource {
  private stop: (() => void) | null = null;
  private fallback = new BrowserNarration();
  private cloudDisabled = false;

  async speak(text: string): Promise<void> {
    this.cancel();
    const clean = stripMarkdown(text);
    if (!clean.trim() || typeof window === "undefined") return;
    if (this.cloudDisabled) return this.fallback.speak(clean);
    const controller = new AbortController();
    let cancelled = false;
    let audio: HTMLAudioElement | null = null;
    let blobUrl: string | null = null;
    let requestTimer: ReturnType<typeof setTimeout> | undefined;
    let playbackTimer: ReturnType<typeof setTimeout> | undefined;
    let finishPlayback: (() => void) | undefined;
    let release: (() => void) | undefined;
    const stopped = new Promise<null>(resolve => { release = () => resolve(null); });
    const cleanupAudio = () => {
      if (playbackTimer) clearTimeout(playbackTimer);
      const previousAudio = audio;
      audio = null;
      if (previousAudio) {
        previousAudio.onended = null; previousAudio.onerror = null;
        try { previousAudio.pause(); } catch { /* Cleanup must still release waiters. */ }
      }
      const previousUrl = blobUrl;
      blobUrl = null;
      if (previousUrl) {
        try { URL.revokeObjectURL(previousUrl); } catch { /* Do not strand cancellation/playback settlement. */ }
      }
    };
    const stop = () => {
      cancelled = true;
      controller.abort();
      if (requestTimer) clearTimeout(requestTimer);
      cleanupAudio(); finishPlayback?.(); release?.();
      this.fallback.cancel();
    };
    this.stop = stop;
    try {
      const timeout = new Promise<never>((_, reject) => {
        requestTimer = setTimeout(() => { controller.abort(); reject(new Error("narration_timeout")); }, 15000);
      });
      // Include body consumption in the deadline, even if transport ignores abort.
      const response = (async () => {
        const res = await fetch(`${API_BASE}/ziwei/tts`, {
          method: "POST", headers: { "Content-Type": "application/json", ...paidRequestHeaders() },
          ...paidRequestOptions(), cache: "no-store", body: JSON.stringify({ text: clean }), signal: controller.signal,
        });
        return { res, blob: res.ok ? await res.blob() : null };
      })();
      const result = await Promise.race([response, timeout, stopped]);
      if (requestTimer) clearTimeout(requestTimer);
      if (cancelled || !result) return;
      if (!result.res.ok) {
        if (paidProduct && result.res.status === 401) { invalidatePaidSession(); return; }
        if (result.res.status === 503) this.cloudDisabled = true;
        await this.fallback.speak(clean);
        return;
      }
      const played = await new Promise<boolean>(resolve => {
        let settled = false;
        const settle = (ok: boolean) => {
          if (settled) return;
          settled = true; cleanupAudio(); resolve(ok);
        };
        finishPlayback = () => settle(false);
        try {
          blobUrl = URL.createObjectURL(result.blob!);
          audio = new Audio(blobUrl);
          audio.onended = () => settle(true);
          audio.onerror = () => settle(false);
          playbackTimer = setTimeout(() => settle(false), 30000);
          void audio.play().catch(() => settle(false));
        } catch { settle(false); }
      });
      if (!played && !cancelled) await this.fallback.speak(clean);
    } catch {
      if (!cancelled) await this.fallback.speak(clean);
    } finally {
      if (requestTimer) clearTimeout(requestTimer);
      cleanupAudio();
      if (this.stop === stop) this.stop = null;
    }
  }

  cancel(): void {
    const stop = this.stop;
    this.stop = null;
    stop?.();
    this.fallback.cancel();
  }
}
