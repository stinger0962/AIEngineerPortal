// frontend/src/lib/ziwei/narration.ts
"use client";

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
    if (!BrowserNarration.isSupported() || !text.trim()) return Promise.resolve();
    return new Promise<void>((resolve) => {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "zh-CN";
      u.rate = 0.92;
      const voice = this.pickVoice();
      if (voice) u.voice = voice;
      // onend 与 onerror 都 resolve：朗读失败时降级为静默继续，绝不卡死指挥器
      u.onend = () => { this.current = null; resolve(); };
      u.onerror = () => { this.current = null; resolve(); };
      this.current = u;
      window.speechSynthesis.speak(u);
    });
  }

  cancel(): void {
    this.current = null;
    if (BrowserNarration.isSupported()) window.speechSynthesis.cancel();
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
