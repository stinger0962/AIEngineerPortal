"use client";

/** 랑이 — a friendly 민화 (folk-art) tiger guide. The 王 on the forehead is the
 * traditional Korean folk-tiger mark (and echoes the boss 왕 seal). Bobs + blinks. */
export function Mascot({ size = 96, className = "", bob = true }: { size?: number; className?: string; bob?: boolean }) {
  return (
    <div className={`${bob ? "k-bob" : ""} ${className}`} style={{ width: size, height: size }}>
      <svg viewBox="0 0 120 120" width={size} height={size} role="img" aria-label="랑이, the tiger guide">
        <defs>
          <radialGradient id="kt-face" cx="50%" cy="38%" r="72%">
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
        <rect x="18" y="22" width="84" height="80" rx="40" fill="url(#kt-face)" stroke="#7a4a1e" strokeWidth="3" />

        {/* forehead 王 mark */}
        <g stroke="#3a2412" strokeWidth="3.4" strokeLinecap="round">
          <path d="M52 33h16" />
          <path d="M50 40h20" />
          <path d="M60 33v13" />
        </g>
        {/* side stripes */}
        <g stroke="#3a2412" strokeWidth="3" strokeLinecap="round" opacity="0.85" fill="none">
          <path d="M22 54q5 3 10 1" />
          <path d="M98 54q-5 3-10 1" />
          <path d="M21 66q5 3 10 1" />
          <path d="M99 66q-5 3-10 1" />
        </g>

        {/* muzzle + blush */}
        <ellipse cx="60" cy="76" rx="27" ry="20" fill="#fff7ee" />
        <circle cx="35" cy="74" r="6" fill="#eaa0a0" opacity="0.6" />
        <circle cx="85" cy="74" r="6" fill="#eaa0a0" opacity="0.6" />

        {/* eyes (blink together) */}
        <g className="k-blink" style={{ transformOrigin: "60px 60px" }}>
          <ellipse cx="46" cy="60" rx="9" ry="10.5" fill="#fff" stroke="#7a4a1e" strokeWidth="2" />
          <ellipse cx="74" cy="60" rx="9" ry="10.5" fill="#fff" stroke="#7a4a1e" strokeWidth="2" />
          <circle cx="47" cy="61" r="4.8" fill="#23303f" />
          <circle cx="73" cy="61" r="4.8" fill="#23303f" />
          <circle cx="48.7" cy="59.2" r="1.6" fill="#fff" />
          <circle cx="74.7" cy="59.2" r="1.6" fill="#fff" />
        </g>

        {/* nose + smile */}
        <path d="M55 71h10l-5 5z" fill="#3a2412" />
        <path d="M60 76q-6 7-12 3M60 76q6 7 12 3" fill="none" stroke="#3a2412" strokeWidth="2.4" strokeLinecap="round" />

        {/* whiskers */}
        <g stroke="#7a4a1e" strokeWidth="1.6" strokeLinecap="round" opacity="0.65">
          <path d="M30 78h12" />
          <path d="M30 84l12-3" />
          <path d="M90 78H78" />
          <path d="M90 84l-12-3" />
        </g>
      </svg>
    </div>
  );
}
