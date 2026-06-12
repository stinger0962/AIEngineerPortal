// frontend/src/lib/ziwei/narration.ts

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

  static isSupported(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  private pickVoice(): SpeechSynthesisVoice | null {
    const voices = window.speechSynthesis.getVoices();
    return (
      voices.find((v) => v.lang === "zh-CN") ??
      voices.find((v) => v.lang?.toLowerCase().startsWith("zh")) ??
      null
    );
  }

  speak(text: string): Promise<void> {
    const spoken = stripMarkdown(text);
    if (!BrowserNarration.isSupported() || !spoken.trim()) return Promise.resolve();
    this.cancel();
    return new Promise<void>((resolve) => {
      const u = new SpeechSynthesisUtterance(spoken);
      u.lang = "zh-CN";
      u.rate = 0.92;
      const voice = this.pickVoice();
      if (voice) u.voice = voice;
      const settle = () => { this.current = null; this.resolveFn = null; resolve(); };
      u.onend = settle;
      u.onerror = settle;
      this.current = u;
      this.resolveFn = resolve;
      window.speechSynthesis.speak(u);
    });
  }

  cancel(): void {
    const r = this.resolveFn;
    this.current = null;
    this.resolveFn = null;
    if (BrowserNarration.isSupported()) window.speechSynthesis.cancel();
    r?.(); // 主动 resolve 在途 Promise——不依赖浏览器是否补发 onend/onerror（Safari 可能都不发）
  }
}

/** 静音/不支持时用：按估算时长定时，让画面编排照常有节拍。 */
export class SilentNarration implements NarrationSource {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private resolveFn: (() => void) | null = null;

  speak(text: string): Promise<void> {
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

/** MiniMax 云端中文嗓音（默认方案）。POST 文本到后端 /ziwei/tts 拿 MP3 播放；
 * 任何失败（未配置 503 / 网络 / 播放）自动回退浏览器语音，绝不卡死调用方。 */
export class CloudNarration implements NarrationSource {
  private audio: HTMLAudioElement | null = null;
  private blobUrl: string | null = null; // 在 cancel 时也能 revoke，避免每次中断泄漏一个对象 URL（解码后的 MP3 驻留内存）
  private controller: AbortController | null = null;
  private resolveFn: (() => void) | null = null;
  private fallback = new BrowserNarration();
  private cloudDisabled = false; // 一旦确认未配置（503）就整场退浏览器，不再无谓请求

  async speak(text: string): Promise<void> {
    const clean = stripMarkdown(text);
    if (!clean.trim() || typeof window === "undefined") return;
    if (this.cloudDisabled) return this.fallback.speak(clean);
    this.cancel();
    const controller = new AbortController();
    this.controller = controller;
    try {
      const res = await fetch(`${API_BASE}/ziwei/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean }),
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (!res.ok) {
        if (res.status === 503) this.cloudDisabled = true;
        return this.fallback.speak(clean);
      }
      const blob = await res.blob();
      if (controller.signal.aborted) return;
      await this.playBlob(blob);
      this.controller = null; // 正常播完，清掉已完成的 controller
    } catch (e) {
      if (controller.signal.aborted || (e instanceof DOMException && e.name === "AbortError")) return;
      return this.fallback.speak(clean);
    }
  }

  private playBlob(blob: Blob): Promise<void> {
    return new Promise<void>((resolve) => {
      const url = URL.createObjectURL(blob);
      this.blobUrl = url;
      const audio = new Audio(url);
      const settle = () => {
        if (this.blobUrl === url) { URL.revokeObjectURL(url); this.blobUrl = null; }
        if (this.audio === audio) this.audio = null;
        this.resolveFn = null;
        resolve();
      };
      audio.onended = settle;
      audio.onerror = settle;
      this.audio = audio;
      this.resolveFn = resolve;
      void audio.play().catch(settle);
    });
  }

  cancel(): void {
    this.controller?.abort();
    this.controller = null;
    this.fallback.cancel();
    const a = this.audio;
    this.audio = null;
    if (a) { a.pause(); a.onended = null; a.onerror = null; }
    if (this.blobUrl) { URL.revokeObjectURL(this.blobUrl); this.blobUrl = null; } // 中断也回收对象 URL，杜绝泄漏
    const r = this.resolveFn;
    this.resolveFn = null;
    r?.();
  }
}
