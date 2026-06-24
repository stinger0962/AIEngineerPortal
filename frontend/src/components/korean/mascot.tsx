"use client";

import { useEffect, useId, useRef, useState } from "react";

export type MascotMood = "happy" | "idle" | "cheer" | "listening" | "thinking" | "correct" | "wrong";

const ANIM: Record<MascotMood, string> = {
  happy: "k-bob",
  idle: "k-bob",
  listening: "k-bob",
  correct: "k-bob",
  cheer: "k-cheer",
  wrong: "k-shake",
  thinking: "k-tilt",
};

const DARK = "#3a2412";

function Eyes({ mood }: { mood: MascotMood }) {
  if (mood === "cheer") {
    // ^_^ joyful closed arcs
    return (
      <g fill="none" stroke={DARK} strokeWidth="2.8" strokeLinecap="round">
        <path d="M39 62q7-8 14 0" />
        <path d="M67 62q7-8 14 0" />
      </g>
    );
  }
  if (mood === "correct") {
    // left open, right wink
    return (
      <g>
        <ellipse cx="46" cy="60" rx="9" ry="10.5" fill="#fff" stroke="#7a4a1e" strokeWidth="2" />
        <circle cx="47" cy="61" r="4.8" fill="#23303f" />
        <circle cx="48.7" cy="59.2" r="1.6" fill="#fff" />
        <path d="M67 61q7 5 14 0" fill="none" stroke={DARK} strokeWidth="2.8" strokeLinecap="round" />
      </g>
    );
  }
  if (mood === "wrong") {
    // small worried eyes + downturned brows
    return (
      <g>
        <circle cx="46" cy="61" r="3.4" fill="#23303f" />
        <circle cx="74" cy="61" r="3.4" fill="#23303f" />
        <g fill="none" stroke="#7a4a1e" strokeWidth="2.4" strokeLinecap="round">
          <path d="M39 52l11 4" />
          <path d="M81 52l-11 4" />
        </g>
      </g>
    );
  }
  // open eyes (happy / idle / listening / thinking); thinking looks up
  const py = mood === "thinking" ? 58.5 : 61;
  const px1 = mood === "thinking" ? 48 : 47;
  const px2 = mood === "thinking" ? 76 : 73;
  return (
    <g className="k-blink" style={{ transformOrigin: "60px 60px" }}>
      <ellipse cx="46" cy="60" rx="9" ry="10.5" fill="#fff" stroke="#7a4a1e" strokeWidth="2" />
      <ellipse cx="74" cy="60" rx="9" ry="10.5" fill="#fff" stroke="#7a4a1e" strokeWidth="2" />
      <circle cx={px1} cy={py} r="4.8" fill="#23303f" />
      <circle cx={px2} cy={py} r="4.8" fill="#23303f" />
      <circle cx={px1 + 1.7} cy={py - 1.8} r="1.6" fill="#fff" />
      <circle cx={px2 + 1.7} cy={py - 1.8} r="1.6" fill="#fff" />
    </g>
  );
}

function Mouth({ mood }: { mood: MascotMood }) {
  if (mood === "cheer") {
    return (
      <g>
        <path d="M49 74q11 13 22 0z" fill="#7a2e22" />
        <path d="M54 78q6 4 12 0" fill="#e98b86" />
      </g>
    );
  }
  if (mood === "wrong") {
    return <path d="M52 85q8-6 16 0" fill="none" stroke={DARK} strokeWidth="2.4" strokeLinecap="round" />;
  }
  if (mood === "thinking") {
    return <ellipse cx="60" cy="80" rx="3.4" ry="4" fill={DARK} />;
  }
  // smile
  return <path d="M60 76q-6 7-12 3M60 76q6 7 12 3" fill="none" stroke={DARK} strokeWidth="2.4" strokeLinecap="round" />;
}

function Accessories({ mood }: { mood: MascotMood }) {
  if (mood === "cheer") {
    return (
      <g fill="var(--kr-gold)">
        <path className="k-twinkle" style={{ transformOrigin: "16px 30px" }} d="M16 24l2 4 4 2-4 2-2 4-2-4-4-2 4-2z" />
        <path className="k-twinkle" style={{ transformOrigin: "104px 26px", animationDelay: "0.3s" }} d="M104 20l2 4 4 2-4 2-2 4-2-4-4-2 4-2z" />
        <path className="k-twinkle" style={{ transformOrigin: "100px 64px", animationDelay: "0.6s" }} d="M100 59l1.6 3.2 3.4 1.6-3.4 1.6-1.6 3.2-1.6-3.2-3.4-1.6 3.4-1.6z" />
      </g>
    );
  }
  if (mood === "listening") {
    return (
      <g fill="none" stroke="var(--celadon-600)" strokeWidth="2.4" strokeLinecap="round" className="k-twinkle" style={{ transformOrigin: "108px 40px" }}>
        <path d="M101 34q5 6 0 12" />
        <path d="M107 30q9 10 0 20" />
      </g>
    );
  }
  if (mood === "thinking") {
    return (
      <g fill="#9aa3ad">
        <circle className="k-twinkle" style={{ transformOrigin: "96px 30px" }} cx="96" cy="30" r="2.2" />
        <circle className="k-twinkle" style={{ transformOrigin: "104px 22px", animationDelay: "0.25s" }} cx="104" cy="22" r="3" />
        <circle className="k-twinkle" style={{ transformOrigin: "112px 13px", animationDelay: "0.5s" }} cx="112" cy="13" r="3.8" />
      </g>
    );
  }
  if (mood === "wrong") {
    // sweat drop
    return <path d="M30 44c3 4 4 6 0 8-4-2-3-4 0-8z" fill="#7fc4e8" stroke="#4a9bc4" strokeWidth="0.8" />;
  }
  return null;
}

/** 랑이 — a 민화 (folk-art) tiger guide. The 王 forehead mark is the traditional
 * Korean folk-tiger sign (and echoes the boss 왕 seal). `mood` drives its expression. */
export function Mascot({ mood = "happy", size = 96, className = "" }: { mood?: MascotMood; size?: number; className?: string }) {
  const gid = useId();
  return (
    <div className={`${ANIM[mood]} ${className}`} style={{ width: size, height: size }}>
      <svg viewBox="0 0 120 120" width={size} height={size} role="img" aria-label="랑이, the tiger guide">
        <defs>
          <radialGradient id={gid} cx="50%" cy="38%" r="72%">
            <stop offset="0%" stopColor="#f7b962" />
            <stop offset="100%" stopColor="#e08a3c" />
          </radialGradient>
        </defs>

        {/* ears */}
        <polygon points="26,32 40,8 52,30" fill="#e08a3c" stroke="#7a4a1e" strokeWidth="2.5" strokeLinejoin="round" />
        <polygon points="94,32 80,8 68,30" fill="#e08a3c" stroke="#7a4a1e" strokeWidth="2.5" strokeLinejoin="round" />
        <polygon points="33,27 40,15 46,27" fill="#bfe0d4" />
        <polygon points="87,27 80,15 74,27" fill="#bfe0d4" />

        {/* head */}
        <rect x="18" y="22" width="84" height="80" rx="40" fill={`url(#${gid})`} stroke="#7a4a1e" strokeWidth="3" />

        {/* forehead 王 mark */}
        <g stroke={DARK} strokeWidth="3.4" strokeLinecap="round">
          <path d="M52 33h16" />
          <path d="M50 40h20" />
          <path d="M60 33v13" />
        </g>
        {/* side stripes */}
        <g stroke={DARK} strokeWidth="3" strokeLinecap="round" opacity="0.85" fill="none">
          <path d="M22 54q5 3 10 1" />
          <path d="M98 54q-5 3-10 1" />
          <path d="M21 66q5 3 10 1" />
          <path d="M99 66q-5 3-10 1" />
        </g>

        {/* muzzle + blush */}
        <ellipse cx="60" cy="76" rx="27" ry="20" fill="#fff7ee" />
        <circle cx="35" cy="74" r="6" fill="#eaa0a0" opacity="0.6" />
        <circle cx="85" cy="74" r="6" fill="#eaa0a0" opacity="0.6" />

        <Eyes mood={mood} />

        {/* nose */}
        <path d="M55 71h10l-5 5z" fill={DARK} />
        <Mouth mood={mood} />

        {/* whiskers */}
        <g stroke="#7a4a1e" strokeWidth="1.6" strokeLinecap="round" opacity="0.65">
          <path d="M30 78h12" />
          <path d="M30 84l12-3" />
          <path d="M90 78H78" />
          <path d="M90 84l-12-3" />
        </g>

        <Accessories mood={mood} />
      </svg>
    </div>
  );
}

/** A small speech bubble pointing left toward the mascot. */
export function SpeechBubble({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div className="k-bounce-in font-kr relative max-w-[230px] rounded-2xl rounded-bl-md border border-ink/10 bg-white/90 px-3.5 py-2 text-sm font-medium text-ink shadow-[0_10px_22px_-12px_rgba(20,33,61,0.45)]">
      {text}
      <span className="absolute -left-1.5 bottom-3 h-3 w-3 rotate-45 border-b border-l border-ink/10 bg-white/90" />
    </div>
  );
}

/** Mascot + its current speech bubble, side by side. */
export function MascotCoach({ mood, bubble, size = 72, className = "" }: { mood: MascotMood; bubble: string; size?: number; className?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Mascot mood={mood} size={size} />
      {bubble && <SpeechBubble text={bubble} />}
    </div>
  );
}

/** Controller for reactive mascot moods. Transient reactions (correct/wrong/cheer/say)
 * auto-return to `base`; steady states (listening/thinking) hold until changed. */
export function useMascot(base: MascotMood = "happy") {
  const [mood, setMood] = useState<MascotMood>(base);
  const [bubble, setBubble] = useState("");
  const timer = useRef<number | undefined>(undefined);

  const clear = () => {
    if (timer.current !== undefined) window.clearTimeout(timer.current);
  };
  useEffect(() => () => clear(), []);
  const flash = (m: MascotMood, msg: string, ms: number) => {
    clear();
    setMood(m);
    setBubble(msg);
    timer.current = window.setTimeout(() => {
      setMood(base);
      setBubble("");
    }, ms);
  };
  const steady = (m: MascotMood, msg: string) => {
    clear();
    setMood(m);
    setBubble(msg);
  };

  return {
    mood,
    bubble,
    correct: (msg = "좋아요! ✓") => flash("correct", msg, 1500),
    wrong: (msg = "괜찮아요, 다시!") => flash("wrong", msg, 1700),
    cheer: (msg = "잘했어요! 🎉") => flash("cheer", msg, 2400),
    say: (msg: string, ms = 2600) => flash(base, msg, ms),
    listening: (msg = "듣고 있어요…") => steady("listening", msg),
    thinking: (msg = "음…") => steady("thinking", msg),
    rest: () => steady(base, ""),
  };
}
