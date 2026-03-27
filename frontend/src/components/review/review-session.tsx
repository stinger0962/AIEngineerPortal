"use client";

import { useState, useCallback, useMemo } from "react";
import {
  RotateCcw,
  ChevronRight,
  ChevronLeft,
  Layers,
  Zap,
  Brain,
  Trophy,
  Flame,
  Sparkles,
  Tag,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { MemoryCard } from "@/lib/types/portal";
import { portalApi } from "@/lib/api/portal";

const CONFIDENCE_LEVELS = [
  { value: 1, label: "Blank", color: "bg-red-400/90 hover:bg-red-400", hint: "No idea" },
  { value: 2, label: "Fuzzy", color: "bg-amber-400/90 hover:bg-amber-400", hint: "Vaguely recall" },
  { value: 3, label: "Close", color: "bg-yellow-300/90 hover:bg-yellow-300", hint: "Most of it" },
  { value: 4, label: "Solid", color: "bg-emerald-400/90 hover:bg-emerald-400", hint: "Got it" },
  { value: 5, label: "Nailed", color: "bg-pine hover:bg-pine/90 text-white", hint: "Cold recall" },
];

const CATEGORY_COLORS: Record<string, string> = {
  agents: "bg-ember/15 text-ember border-ember/25",
  rag: "bg-pine/15 text-pine border-pine/25",
  "llm-fundamentals": "bg-indigo-100 text-indigo-700 border-indigo-200",
  evaluation: "bg-mint text-pine border-pine/20",
  python: "bg-amber-100 text-amber-800 border-amber-200",
  deployment: "bg-slate-100 text-slate-700 border-slate-200",
};

const DIFFICULTY_BADGE: Record<string, string> = {
  beginner: "bg-mint/60 text-pine",
  intermediate: "bg-sand text-ink",
  advanced: "bg-ember/15 text-ember",
};

const SOURCE_ICON: Record<string, typeof Brain> = {
  lesson: Brain,
  exercise: Zap,
  interview: Sparkles,
  knowledge: Layers,
};

function renderMarkdown(md: string) {
  // Lightweight markdown: bold, code blocks, inline code, bullets, headers
  const lines = md.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeKey = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`code-${codeKey++}`}
            className="my-3 overflow-x-auto rounded-xl bg-ink/[0.04] px-4 py-3 font-mono text-[13px] leading-relaxed text-ink/85"
          >
            {codeLines.join("\n")}
          </pre>
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    // Process inline formatting
    const processInline = (text: string) => {
      const parts: React.ReactNode[] = [];
      let remaining = text;
      let partKey = 0;

      while (remaining.length > 0) {
        // Bold
        const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
        // Inline code
        const codeMatch = remaining.match(/`([^`]+)`/);

        const boldIdx = boldMatch ? remaining.indexOf(boldMatch[0]) : Infinity;
        const codeIdx = codeMatch ? remaining.indexOf(codeMatch[0]) : Infinity;

        if (boldIdx === Infinity && codeIdx === Infinity) {
          parts.push(<span key={partKey++}>{remaining}</span>);
          break;
        }

        if (boldIdx <= codeIdx && boldMatch) {
          if (boldIdx > 0) parts.push(<span key={partKey++}>{remaining.slice(0, boldIdx)}</span>);
          parts.push(
            <strong key={partKey++} className="font-semibold text-ink">
              {boldMatch[1]}
            </strong>
          );
          remaining = remaining.slice(boldIdx + boldMatch[0].length);
        } else if (codeMatch) {
          if (codeIdx > 0) parts.push(<span key={partKey++}>{remaining.slice(0, codeIdx)}</span>);
          parts.push(
            <code
              key={partKey++}
              className="rounded-md bg-ink/[0.06] px-1.5 py-0.5 font-mono text-[13px] text-ink/90"
            >
              {codeMatch[1]}
            </code>
          );
          remaining = remaining.slice(codeIdx + codeMatch[0].length);
        }
      }
      return parts;
    };

    if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex gap-2 pl-1">
          <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-ember/50" />
          <span className="text-[15px] leading-relaxed text-ink/80">{processInline(line.slice(2))}</span>
        </div>
      );
    } else if (line.match(/^\d+\.\s/)) {
      const num = line.match(/^(\d+)\.\s(.*)/)!;
      elements.push(
        <div key={i} className="flex gap-2.5 pl-1">
          <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-ink/[0.07] font-mono text-[11px] font-bold text-ink/60">
            {num[1]}
          </span>
          <span className="text-[15px] leading-relaxed text-ink/80">{processInline(num[2])}</span>
        </div>
      );
    } else {
      elements.push(
        <p key={i} className="text-[15px] leading-relaxed text-ink/80">
          {processInline(line)}
        </p>
      );
    }
  }

  return <div className="space-y-1">{elements}</div>;
}

type ReviewState = "browsing" | "reviewing" | "complete";

export function ReviewSession({ cards }: { cards: MemoryCard[] }) {
  const [state, setState] = useState<ReviewState>("browsing");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [deck, setDeck] = useState<MemoryCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [scores, setScores] = useState<Record<number, number>>({});
  const [isTransitioning, setIsTransitioning] = useState(false);

  const categories = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const card of cards) {
      counts[card.category] = (counts[card.category] || 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [cards]);

  const filteredCards = useMemo(() => {
    if (!selectedCategory) return cards;
    return cards.filter((c) => c.category === selectedCategory);
  }, [cards, selectedCategory]);

  const startReview = useCallback(
    (subset?: MemoryCard[]) => {
      const reviewDeck = subset ?? filteredCards;
      setDeck(reviewDeck);
      setCurrentIndex(0);
      setIsFlipped(false);
      setScores({});
      setState("reviewing");
    },
    [filteredCards]
  );

  const currentCard = deck[currentIndex];

  const handleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const handleConfidence = useCallback(
    async (confidence: number) => {
      if (!currentCard) return;

      setScores((prev) => ({ ...prev, [currentCard.id]: confidence }));

      try {
        await portalApi.reviewMemoryCard(currentCard.id, confidence);
      } catch {
        // mock fallback handles it
      }

      if (currentIndex < deck.length - 1) {
        setIsTransitioning(true);
        setTimeout(() => {
          setCurrentIndex((prev) => prev + 1);
          setIsFlipped(false);
          setIsTransitioning(false);
        }, 300);
      } else {
        setState("complete");
      }
    },
    [currentCard, currentIndex, deck.length]
  );

  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentIndex((prev) => prev - 1);
        setIsFlipped(false);
        setIsTransitioning(false);
      }, 300);
    }
  }, [currentIndex]);

  const sessionStats = useMemo(() => {
    const vals = Object.values(scores);
    if (vals.length === 0) return null;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const strong = vals.filter((v) => v >= 4).length;
    const weak = vals.filter((v) => v <= 2).length;
    return { avg, strong, weak, total: vals.length };
  }, [scores]);

  // ─── BROWSING STATE ───────────────────────────────
  if (state === "browsing") {
    return (
      <div className="space-y-8">
        {/* Category filter */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={cn(
              "rounded-full border px-4 py-2 text-sm font-medium transition-all",
              !selectedCategory
                ? "border-ink bg-ink text-white shadow-md"
                : "border-ink/15 bg-white/60 text-ink/70 hover:border-ink/30 hover:text-ink"
            )}
          >
            All cards ({cards.length})
          </button>
          {categories.map(([cat, count]) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-medium transition-all",
                cat === selectedCategory
                  ? "border-ink bg-ink text-white shadow-md"
                  : "border-ink/15 bg-white/60 text-ink/70 hover:border-ink/30 hover:text-ink"
              )}
            >
              {cat.replace(/-/g, " ")} ({count})
            </button>
          ))}
        </div>

        {/* Start review CTA */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => startReview()}
            className="group flex items-center gap-3 rounded-2xl bg-ink px-6 py-3.5 font-semibold text-white shadow-lg transition-all hover:shadow-xl hover:brightness-110"
          >
            <Layers size={18} className="transition-transform group-hover:rotate-12" />
            Start review ({filteredCards.length} cards)
          </button>
          {filteredCards.some((c) => (c.confidence ?? 0) <= 2) && (
            <button
              onClick={() => startReview(filteredCards.filter((c) => (c.confidence ?? 0) <= 2))}
              className="flex items-center gap-2 rounded-2xl border border-ember/30 bg-ember/10 px-5 py-3.5 text-sm font-semibold text-ember transition-all hover:bg-ember/20"
            >
              <Flame size={16} />
              Weak cards only ({filteredCards.filter((c) => (c.confidence ?? 0) <= 2).length})
            </button>
          )}
        </div>

        {/* Card grid preview */}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filteredCards.map((card) => {
            const SourceIcon = SOURCE_ICON[card.source_kind] ?? Brain;
            return (
              <div
                key={card.id}
                className="group relative overflow-hidden rounded-[22px] border border-ink/[0.08] bg-white/80 p-5 shadow-sm backdrop-blur transition-all hover:border-ink/15 hover:shadow-md"
              >
                {/* Category edge accent */}
                <div
                  className={cn(
                    "absolute left-0 top-0 h-full w-1 rounded-l-[22px]",
                    card.category === "agents"
                      ? "bg-ember"
                      : card.category === "rag"
                        ? "bg-pine"
                        : card.category === "evaluation"
                          ? "bg-emerald-500"
                          : "bg-indigo-400"
                  )}
                />

                <div className="space-y-3 pl-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide",
                          CATEGORY_COLORS[card.category] ?? "bg-slate-100 text-slate-600 border-slate-200"
                        )}
                      >
                        <Tag size={10} />
                        {card.category.replace(/-/g, " ")}
                      </span>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                          DIFFICULTY_BADGE[card.difficulty]
                        )}
                      >
                        {card.difficulty}
                      </span>
                    </div>
                    <SourceIcon size={14} className="mt-1 text-ink/30" />
                  </div>

                  <p className="text-[14px] font-medium leading-snug text-ink/85">
                    {card.front_md.replace(/\*\*/g, "").slice(0, 100)}
                    {card.front_md.length > 100 ? "..." : ""}
                  </p>

                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-ink/40">
                      {card.review_count > 0 ? `Reviewed ${card.review_count}×` : "Not yet reviewed"}
                    </span>
                    {card.confidence != null && (
                      <div className="flex gap-0.5">
                        {[1, 2, 3, 4, 5].map((dot) => (
                          <div
                            key={dot}
                            className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              dot <= card.confidence! ? "bg-pine" : "bg-ink/10"
                            )}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ─── REVIEW COMPLETE ──────────────────────────────
  if (state === "complete" && sessionStats) {
    return (
      <div className="mx-auto max-w-lg space-y-8 py-8">
        <div className="rounded-[28px] border border-ink/[0.08] bg-white/85 p-8 shadow-panel backdrop-blur">
          <div className="space-y-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-mint">
              <Trophy size={28} className="text-pine" />
            </div>
            <div>
              <h3 className="font-display text-2xl text-ink">Session complete</h3>
              <p className="mt-1 text-sm text-ink/60">{sessionStats.total} cards reviewed</p>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-2xl bg-cream p-4">
                <div className="font-display text-2xl text-ink">
                  {sessionStats.avg.toFixed(1)}
                </div>
                <div className="text-[11px] uppercase tracking-wider text-ink/50">Avg confidence</div>
              </div>
              <div className="rounded-2xl bg-mint/50 p-4">
                <div className="font-display text-2xl text-pine">{sessionStats.strong}</div>
                <div className="text-[11px] uppercase tracking-wider text-ink/50">Strong</div>
              </div>
              <div className="rounded-2xl bg-ember/10 p-4">
                <div className="font-display text-2xl text-ember">{sessionStats.weak}</div>
                <div className="text-[11px] uppercase tracking-wider text-ink/50">Need work</div>
              </div>
            </div>

            {/* Per-card results */}
            <div className="space-y-2 pt-2">
              {deck.map((card) => (
                <div
                  key={card.id}
                  className="flex items-center gap-3 rounded-xl bg-cream/60 px-4 py-2.5 text-left"
                >
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((dot) => (
                      <div
                        key={dot}
                        className={cn(
                          "h-2 w-2 rounded-full transition-colors",
                          dot <= (scores[card.id] ?? 0)
                            ? scores[card.id] >= 4
                              ? "bg-pine"
                              : scores[card.id] >= 3
                                ? "bg-yellow-400"
                                : "bg-red-400"
                            : "bg-ink/10"
                        )}
                      />
                    ))}
                  </div>
                  <span className="flex-1 truncate text-sm text-ink/75">
                    {card.front_md.replace(/\*\*/g, "").slice(0, 60)}...
                  </span>
                </div>
              ))}
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => {
                  const weakCards = deck.filter((c) => (scores[c.id] ?? 0) <= 2);
                  if (weakCards.length > 0) {
                    startReview(weakCards);
                  } else {
                    setState("browsing");
                  }
                }}
                className="flex flex-1 items-center justify-center gap-2 rounded-2xl border border-ember/30 bg-ember/10 px-4 py-3 text-sm font-semibold text-ember transition hover:bg-ember/20"
              >
                <RotateCcw size={15} />
                Retry weak cards
              </button>
              <button
                onClick={() => setState("browsing")}
                className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110"
              >
                Back to deck
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── REVIEWING STATE ──────────────────────────────
  if (!currentCard) return null;

  const SourceIcon = SOURCE_ICON[currentCard.source_kind] ?? Brain;
  const progress = ((currentIndex + 1) / deck.length) * 100;

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-ink/50">
            Card {currentIndex + 1} of {deck.length}
          </span>
          <span className="font-medium text-ink/70">
            {Object.keys(scores).length} reviewed
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-ink/[0.06]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-pine to-ember transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* The card */}
      <div className="perspective-[1200px]">
        <div
          onClick={handleFlip}
          className={cn(
            "memory-card-inner relative cursor-pointer",
            isFlipped && "memory-card-flipped",
            isTransitioning && "opacity-0 scale-95"
          )}
          style={{
            transition: isTransitioning
              ? "opacity 0.25s ease, transform 0.25s ease"
              : "transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
            transformStyle: "preserve-3d",
          }}
        >
          {/* FRONT */}
          <div
            className="memory-card-face rounded-[28px] border border-ink/[0.08] bg-white/90 shadow-panel backdrop-blur"
            style={{ backfaceVisibility: "hidden" }}
          >
            <div className="p-8">
              {/* Card header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide",
                      CATEGORY_COLORS[currentCard.category] ?? "bg-slate-100 text-slate-600 border-slate-200"
                    )}
                  >
                    <Tag size={10} />
                    {currentCard.category.replace(/-/g, " ")}
                  </span>
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider",
                      DIFFICULTY_BADGE[currentCard.difficulty]
                    )}
                  >
                    {currentCard.difficulty}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-ink/35">
                  <SourceIcon size={14} />
                  <span className="text-[11px]">{currentCard.source_title}</span>
                </div>
              </div>

              {/* Question */}
              <div className="mt-8 mb-12 min-h-[140px]">
                <div className="text-[17px] font-medium leading-relaxed text-ink/90">
                  {renderMarkdown(currentCard.front_md)}
                </div>
              </div>

              {/* Flip hint */}
              <div className="flex items-center justify-center gap-2 text-sm text-ink/30">
                <RotateCcw size={14} />
                <span>Click to reveal answer</span>
              </div>
            </div>
          </div>

          {/* BACK */}
          <div
            className="memory-card-face memory-card-back absolute inset-0 rounded-[28px] border border-pine/15 bg-gradient-to-br from-white/95 to-mint/20 shadow-panel backdrop-blur"
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
          >
            <div className="p-8">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-pine/70">
                  Answer
                </p>
                <span className="text-[11px] text-ink/35">{currentCard.source_title}</span>
              </div>

              <div className="mt-5 max-h-[400px] overflow-y-auto pr-2">
                {renderMarkdown(currentCard.back_md)}
              </div>

              <div className="mt-6 flex items-center justify-center gap-2 text-sm text-pine/40">
                <RotateCcw size={14} />
                <span>Click to see question</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confidence rating — only visible when flipped */}
      <div
        className={cn(
          "space-y-3 transition-all duration-300",
          isFlipped ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-4 opacity-0"
        )}
      >
        <p className="text-center text-sm font-medium text-ink/50">How well did you know this?</p>
        <div className="flex justify-center gap-2">
          {CONFIDENCE_LEVELS.map((level) => (
            <button
              key={level.value}
              onClick={(e) => {
                e.stopPropagation();
                handleConfidence(level.value);
              }}
              className={cn(
                "group relative rounded-xl px-4 py-2.5 text-sm font-semibold transition-all hover:scale-105 hover:shadow-md",
                level.color
              )}
            >
              {level.label}
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-ink px-2.5 py-1 text-[11px] text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {level.hint}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className={cn(
            "flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm transition",
            currentIndex === 0
              ? "cursor-not-allowed text-ink/20"
              : "text-ink/50 hover:bg-ink/5 hover:text-ink"
          )}
        >
          <ChevronLeft size={16} />
          Previous
        </button>
        <button
          onClick={() => setState("browsing")}
          className="rounded-xl px-4 py-2 text-sm text-ink/40 transition hover:bg-ink/5 hover:text-ink"
        >
          End session
        </button>
        <button
          onClick={() => {
            if (currentIndex < deck.length - 1) {
              setIsTransitioning(true);
              setTimeout(() => {
                setCurrentIndex((prev) => prev + 1);
                setIsFlipped(false);
                setIsTransitioning(false);
              }, 300);
            }
          }}
          disabled={currentIndex === deck.length - 1}
          className={cn(
            "flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm transition",
            currentIndex === deck.length - 1
              ? "cursor-not-allowed text-ink/20"
              : "text-ink/50 hover:bg-ink/5 hover:text-ink"
          )}
        >
          Skip
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
