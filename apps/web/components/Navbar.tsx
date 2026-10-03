"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-surface-container-lowest/90 backdrop-blur-sm border-b border-ink-border">
      <div className="h-16 max-w-[1040px] mx-auto px-4 md:px-8 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-xs tracking-[0.25em] uppercase font-semibold text-ink-primary hover:text-primary-container transition-colors select-none"
          >
            SANKALP
          </Link>
          <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-surface-container text-ink-secondary border border-ink-border">
            Transit Recovery Prototype
          </span>
        </div>

        <div className="flex items-center gap-6">
          <nav className="flex items-center gap-4 text-xs font-medium">
            <Link
              href="/"
              className={`transition-colors py-1 ${
                pathname === "/"
                  ? "text-ink-primary font-semibold border-b-2 border-primary-container"
                  : "text-ink-muted hover:text-ink-primary"
              }`}
            >
              Search
            </Link>
            <Link
              href="/results"
              className={`transition-colors py-1 ${
                pathname.startsWith("/results")
                  ? "text-ink-primary font-semibold border-b-2 border-primary-container"
                  : "text-ink-muted hover:text-ink-primary"
              }`}
            >
              Alternatives
            </Link>
          </nav>

          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="System Operational" />
            <div className="w-7 h-7 rounded-full bg-primary-container text-white flex items-center justify-center text-xs font-medium">
              SK
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
