// Subtle "door opening" sound, synthesized live via Web Audio — no audio asset
// (keeps it China-safe: nothing to fetch, nothing to be blocked). Must be called
// from a user gesture (a click) so browsers allow it to play.
//
// Three layered voices over ~1.4s:
//   1. a low wooden "thunk" as the latch releases
//   2. a filtered-noise creak/whoosh that sweeps up as the leaves swing
//   3. a faint high resonance that blooms as light spills through

let ctx: AudioContext | null = null;

type WebkitWindow = Window & { webkitAudioContext?: typeof AudioContext };

export function playDoorOpen(): void {
  if (typeof window === "undefined") return;
  try {
    const AC = window.AudioContext ?? (window as WebkitWindow).webkitAudioContext;
    if (!AC) return;
    if (!ctx) ctx = new AC();
    if (ctx.state === "suspended") void ctx.resume();

    const now = ctx.currentTime;
    const master = ctx.createGain();
    master.connect(ctx.destination);
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.16, now + 0.06);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);

    // 1) wooden thunk
    const thunk = ctx.createOscillator();
    thunk.type = "triangle";
    thunk.frequency.setValueAtTime(124, now);
    thunk.frequency.exponentialRampToValueAtTime(58, now + 0.26);
    const tg = ctx.createGain();
    tg.gain.setValueAtTime(0.6, now);
    tg.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    thunk.connect(tg).connect(master);
    thunk.start(now);
    thunk.stop(now + 0.32);

    // 2) creak / whoosh — filtered noise sweeping up
    const dur = 1.2;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1) * 0.5;
    const noise = ctx.createBufferSource();
    noise.buffer = buf;
    const bp = ctx.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.setValueAtTime(280, now);
    bp.frequency.exponentialRampToValueAtTime(1200, now + 0.9);
    bp.Q.value = 0.8;
    const ng = ctx.createGain();
    ng.gain.setValueAtTime(0.0001, now);
    ng.gain.exponentialRampToValueAtTime(0.22, now + 0.2);
    ng.gain.exponentialRampToValueAtTime(0.0001, now + 1.1);
    noise.connect(bp).connect(ng).connect(master);
    noise.start(now);
    noise.stop(now + dur);

    // 3) faint resonance as light spills
    const shimmer = ctx.createOscillator();
    shimmer.type = "sine";
    shimmer.frequency.setValueAtTime(868, now + 0.5);
    const sg = ctx.createGain();
    sg.gain.setValueAtTime(0.0001, now + 0.5);
    sg.gain.exponentialRampToValueAtTime(0.07, now + 0.72);
    sg.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);
    shimmer.connect(sg).connect(master);
    shimmer.start(now + 0.5);
    shimmer.stop(now + 1.45);
  } catch {
    // Audio is a nice-to-have; never let it break navigation.
  }
}
