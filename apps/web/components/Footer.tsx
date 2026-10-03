import Link from "next/link";

export default function Footer() {
  return (
    <footer className="w-full bg-surface-container-lowest border-t border-ink-border py-8 mt-auto">
      <div className="max-w-[1040px] mx-auto px-4 md:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-muted">
        <div className="flex flex-col sm:flex-row items-center gap-2">
          <span className="font-semibold tracking-[0.1em] uppercase text-ink-primary">
            SANKALP · Autonomous Transit Recovery
          </span>
          <span className="hidden sm:inline text-ink-border">·</span>
          <span>Simulated schedules based on static network data.</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[11px] text-ink-muted">Deterministic Monte Carlo Decision Engine</span>
        </div>
      </div>
    </footer>
  );
}
