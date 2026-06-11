// frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts
"use client";

import { useRef, useCallback } from "react";
import type { CameraCommand, OracleSegment, OracleStreamHandlers } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "../term-card";
import { fireCamera } from "./camera";
import { BrowserNarration, SilentNarration, type NarrationSource } from "@/lib/ziwei/narration";

const SETTLE_MS = 550;
const GAP_MS = 300;
const EMPTY_DWELL_MS = 900;

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** 一拍 =（前导文字 + 紧随的镜头指令）。command 为 null 表示收尾无镜头段。 */
type Beat = { text: string; command: CameraCommand | null };

/** 单生产者/单消费者异步队列：流处理器 push，表演循环 next。 */
class BeatQueue {
  private items: Beat[] = [];
  private closed = false;
  private waiter: (() => void) | null = null;
  convId: number | null = null;
  errored = false;

  push(b: Beat): void {
    this.items.push(b);
    this.wake();
  }
  close(convId: number | null, errored = false): void {
    this.convId = convId;
    this.errored = errored;
    this.closed = true;
    this.wake();
  }
  private wake(): void {
    const w = this.waiter;
    this.waiter = null;
    w?.();
  }
  /** 取下一拍；队空且已关闭 → null。 */
  async next(): Promise<Beat | null> {
    while (true) {
      if (this.items.length) return this.items.shift()!;
      if (this.closed) return null;
      await new Promise<void>((res) => { this.waiter = res; });
    }
  }
}

function captionFor(cmd: CameraCommand | null): string {
  if (!cmd) return "";
  if (cmd.type === "focus_palace") return ` · ${cmd.palace}`;
  if (cmd.type === "overview") return " · 通盘";
  if (cmd.type === "explain_term") return ` · ${cmd.term}`;
  return "";
}

export type TourDeps = {
  chart: ZiweiChart;
  onFocusBranch: (b: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  onCaption: (c: string | null) => void;
  onReveal: (full: string) => void;
  onTourActiveChange: (active: boolean) => void;
  reducedMotion: boolean;
};

export function useOracleTour() {
  const queueRef = useRef<BeatQueue | null>(null);
  const browserRef = useRef<NarrationSource | null>(null);
  const silentRef = useRef<NarrationSource>(new SilentNarration());
  const mutedRef = useRef(false);
  const skippedRef = useRef(false);
  // 每次解读一枚身份令牌：play 进入时捕获，runRef 一旦被换（cancel 或新解读 begin）即视为作废，
  // 避免「快速再问」时旧的 play 循环复活、把镜头/文字泼到新解读上。
  const runRef = useRef<object>({});

  // 仅依据 mute 选源；作废与否由 play 的令牌检查负责（作废的循环根本走不到 speak）。
  const getNarration = (): NarrationSource => {
    if (mutedRef.current) return silentRef.current;
    if (!browserRef.current) browserRef.current = new BrowserNarration();
    return browserRef.current;
  };

  const begin = useCallback((): { queue: BeatQueue; handlers: OracleStreamHandlers } => {
    const token = {};
    runRef.current = token;
    queueRef.current = null;
    skippedRef.current = false;
    const queue = new BeatQueue();
    queueRef.current = queue;
    let buf = "";
    const handlers: OracleStreamHandlers = {
      onText: (delta) => { buf += delta; },
      onCamera: (command) => { queue.push({ text: buf, command }); buf = ""; },
      onDone: (cid) => {
        if (buf.trim()) queue.push({ text: buf, command: null });
        buf = "";
        queue.close(cid, false);
      },
      onError: () => {
        if (buf.trim()) queue.push({ text: buf, command: null });
        buf = "";
        queue.close(null, true);
      },
    };
    return { queue, handlers };
  }, []);

  const play = useCallback(async (queue: BeatQueue, deps: TourDeps): Promise<void> => {
    const myToken = runRef.current;
    const isStale = () => runRef.current !== myToken;
    deps.onTourActiveChange(true);
    let full = "";
    try {
      while (true) {
        const beat = await queue.next();
        if (beat === null) break;
        full += beat.text;

        if (isStale()) continue;                       // 被取消/被新解读取代 → 静默排空，不表演不揭晓
        if (skippedRef.current || deps.reducedMotion) {
          deps.onReveal(full.trim());                  // 跳过/降级：直出已得全文
          continue;
        }
        deps.onCaption(captionFor(beat.command));
        if (beat.command) fireCamera(beat.command, { chart: deps.chart, onFocusBranch: deps.onFocusBranch, onTerm: deps.onTerm });
        await sleep(SETTLE_MS);
        if (isStale()) continue;
        if (beat.text.trim()) await getNarration().speak(beat.text.trim());
        else await sleep(EMPTY_DWELL_MS);
        await sleep(GAP_MS);
      }
      if (!isStale()) {                                // 正常收尾：tourActive 仍为 true，镜头以解读速度缓缓回总览
        deps.onReveal(full.trim());
        deps.onTerm(null);
        deps.onFocusBranch(null);
      }
    } finally {
      deps.onCaption(null);
      deps.onTourActiveChange(false);
    }
  }, []);

  const skip = useCallback(() => {
    skippedRef.current = true;
    browserRef.current?.cancel();
    silentRef.current.cancel();
  }, []);

  const cancel = useCallback(() => {
    runRef.current = {};                               // 换令牌作废所有在跑的循环
    browserRef.current?.cancel();
    silentRef.current.cancel();
    queueRef.current?.close(null, false);
  }, []);

  const setMuted = useCallback((muted: boolean) => {
    mutedRef.current = muted;
    if (muted) browserRef.current?.cancel();
  }, []);

  const beginFromSegments = useCallback((segments: OracleSegment[]): BeatQueue => {
    const token = {};
    runRef.current = token;
    skippedRef.current = false;
    const queue = new BeatQueue();
    queueRef.current = queue;
    for (const seg of segments) {
      const cmd = seg.commands[0] ?? null;
      queue.push({ text: seg.text ?? "", command: cmd });
    }
    queue.close(null, false);
    return queue;
  }, []);

  return { begin, play, skip, cancel, setMuted, beginFromSegments };
}
