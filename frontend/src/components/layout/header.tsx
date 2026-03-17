export function Header() {
  return (
    <header className="flex items-center justify-between rounded-[28px] border border-white/50 bg-white/80 px-6 py-4 shadow-panel backdrop-blur">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Phase 1 MVP</p>
        <h1 className="font-display text-2xl text-ink">Build career momentum with visible, repeatable progress.</h1>
      </div>
      <div className="rounded-full border border-ink/10 bg-cream px-4 py-2 text-sm text-ink/70">Single-user private mode</div>
    </header>
  );
}
