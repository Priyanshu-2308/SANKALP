"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import StationAutocomplete from "../components/StationAutocomplete";
import { parseNaturalLanguageQuery } from "../lib/api";
import { Place } from "../lib/types";

export default function HomePage() {
  const router = useRouter();

  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [deadline, setDeadline] = useState<string>("");
  const [budgetInr, setBudgetInr] = useState<number>(4500);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Chat Box state
  const [nlQuery, setNlQuery] = useState("");
  const [isParsingNl, setIsParsingNl] = useState(false);
  const [isParserAvailable, setIsParserAvailable] = useState(true);

  // Initialize deadline to 18 hours from now
  useEffect(() => {
    const d = new Date(Date.now() + 18 * 60 * 60 * 1000);
    const pad = (n: number) => String(n).padStart(2, "0");
    const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    setDeadline(formatted);
  }, []);

  const handleSwap = () => {
    const temp = origin;
    setOrigin(destination);
    setDestination(temp);
  };

  const handleParseNl = async () => {
    const textToParse = nlQuery.trim();
    if (!textToParse) return;

    setIsParsingNl(true);
    setFormError(null);

    try {
      const res = await parseNaturalLanguageQuery(textToParse);
      if (res.origin) setOrigin(res.origin);
      if (res.destination) setDestination(res.destination);
      if (res.budget_inr) setBudgetInr(res.budget_inr);

      if (res.deadline) {
        const d = new Date(res.deadline);
        const pad = (n: number) => String(n).padStart(2, "0");
        const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        setDeadline(formatted);
      }
    } catch (err: any) {
      const msg = String(err?.message || "").toLowerCase();
      // If AI parser is unavailable (no key or quota hit), hide the chat box completely
      if (
        msg.includes("quota") ||
        msg.includes("key") ||
        msg.includes("unauthorized") ||
        msg.includes("unavailable") ||
        msg.includes("429") ||
        msg.includes("401") ||
        msg.includes("403") ||
        msg.includes("not found")
      ) {
        setIsParserAvailable(false);
      }
    } finally {
      setIsParsingNl(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!origin) {
      setFormError("Please select a departure station or airport.");
      return;
    }
    if (!destination) {
      setFormError("Please select an arrival destination.");
      return;
    }
    if (origin.id === destination.id) {
      setFormError("Origin and destination must be different transit hubs.");
      return;
    }
    if (!deadline) {
      setFormError("Please select a required arrival deadline.");
      return;
    }

    setIsSubmitting(true);
    const deadlineIso = new Date(deadline).toISOString();
    const budgetPaise = Math.round(budgetInr * 100);

    const queryParams = new URLSearchParams({
      origin_id: origin.id,
      destination_id: destination.id,
      deadline: deadlineIso,
      budget_paise: String(budgetPaise),
    });

    router.push(`/results?${queryParams.toString()}`);
  };

  return (
    <div className="w-full flex-1 flex flex-col items-center justify-center px-4 py-12 md:py-16">
      <div className="w-full max-w-[620px] flex flex-col items-center">
        {/* Headline */}
        <div className="text-center mb-6">
          <h1 className="text-3xl md:text-4xl font-semibold text-ink-primary tracking-tight">
            Find your alternative route.
          </h1>
        </div>

        {/* Minimalist Chat Box */}
        {isParserAvailable && (
          <div className="w-full relative mb-6">
            <input
              type="text"
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleParseNl();
                }
              }}
              placeholder="How can I help?"
              className="w-full bg-surface-container-lowest border border-ink-border rounded-xl pl-4 pr-11 py-3 text-sm text-ink-primary shadow-xs focus:outline-none focus:border-ink-primary placeholder:text-ink-muted transition-colors"
            />
            <button
              type="button"
              onClick={() => handleParseNl()}
              disabled={isParsingNl || !nlQuery.trim()}
              aria-label="Submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-ink-muted hover:text-ink-primary hover:bg-surface-container transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
            >
              {isParsingNl ? (
                <div className="w-4 h-4 border-2 border-primary-container border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M14 5l7 7m0 0l-7 7m7-7H3"
                  />
                </svg>
              )}
            </button>
          </div>
        )}

        {/* Structured Search Form */}
        <form
          onSubmit={handleSubmit}
          className="w-full bg-surface-container-lowest border border-ink-border rounded-xl p-6 md:p-8 shadow-sm flex flex-col gap-5"
        >
          {formError && (
            <div className="p-3 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative">
            <StationAutocomplete
              id="origin-input"
              label="From"
              placeholder="Departure hub or city"
              value={origin}
              onSelect={setOrigin}
              required
            />

            <StationAutocomplete
              id="destination-input"
              label="To"
              placeholder="Destination hub or city"
              value={destination}
              onSelect={setDestination}
              required
            />

            {/* Middle swap button on desktop */}
            <button
              type="button"
              onClick={handleSwap}
              title="Swap stations"
              className="hidden md:flex absolute left-1/2 top-[34px] -translate-x-1/2 z-10 w-7 h-7 bg-surface-container-lowest border border-ink-border rounded-full items-center justify-center text-ink-muted hover:text-ink-primary transition-colors shadow-xs"
            >
              ⇄
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label
                htmlFor="deadline-input"
                className="text-xs font-medium text-ink-secondary"
              >
                Must arrive by
              </label>
              <input
                id="deadline-input"
                type="datetime-local"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                required
                className="w-full bg-surface-container-lowest border border-ink-border rounded-lg px-3 py-2.5 text-sm text-ink-primary focus:outline-none focus:border-ink-primary transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label
                htmlFor="budget-input"
                className="text-xs font-medium text-ink-secondary"
              >
                Maximum Budget (₹)
              </label>
              <input
                id="budget-input"
                type="number"
                min="300"
                max="50000"
                step="100"
                value={budgetInr}
                onChange={(e) => setBudgetInr(Number(e.target.value))}
                placeholder="e.g. 4500"
                required
                className="w-full bg-surface-container-lowest border border-ink-border rounded-lg px-3 py-2.5 text-sm text-ink-primary focus:outline-none focus:border-ink-primary transition-colors"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-primary-container hover:bg-primary-hover active:bg-primary-active text-white text-sm font-medium py-3 rounded-lg transition-colors flex items-center justify-center gap-2 select-none"
            >
              {isSubmitting ? (
                <span>Running 10,000 Monte Carlo Simulations...</span>
              ) : (
                <span>Compute Recovery Itineraries</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
