"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import StationAutocomplete from "../components/StationAutocomplete";
import { getPlaceById } from "../lib/api";
import { Place } from "../lib/types";

export default function HomePage() {
  const router = useRouter();

  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [deadline, setDeadline] = useState<string>("");
  const [budgetInr, setBudgetInr] = useState<number>(4500);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Initialize deadline to 18 hours from now
  useEffect(() => {
    const d = new Date(Date.now() + 18 * 60 * 60 * 1000);
    // Format to YYYY-MM-DDTHH:mm
    const pad = (n: number) => String(n).padStart(2, "0");
    const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    setDeadline(formatted);
  }, []);

  const handleSwap = () => {
    const temp = origin;
    setOrigin(destination);
    setDestination(temp);
  };

  const handleQuickSelect = async (origCode: string, destCode: string, budget: number) => {
    try {
      const [origPlace, destPlace] = await Promise.all([
        getPlaceById(origCode),
        getPlaceById(destCode),
      ]);
      setOrigin(origPlace);
      setDestination(destPlace);
      setBudgetInr(budget);
    } catch (e) {
      console.error("Quick select error:", e);
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
        {/* Hero Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-semibold text-ink-primary tracking-tight">
            Find your alternative route.
          </h1>
          <p className="text-sm md:text-base text-ink-secondary mt-2">
            Autonomous multi-modal recovery when Indian transit schedules fail.
          </p>
        </div>

        {/* Search Card */}
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
              <label htmlFor="deadline-input" className="text-xs font-medium text-ink-secondary">
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
              <label htmlFor="budget-input" className="text-xs font-medium text-ink-secondary">
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

        {/* Quick Corridor Buttons */}
        <div className="flex items-center gap-2 mt-6 text-xs text-ink-muted flex-wrap justify-center">
          <span>Quick corridors:</span>
          <button
            type="button"
            onClick={() => handleQuickSelect("NDLS", "JP", 1800)}
            className="hover:text-ink-primary transition-colors underline underline-offset-4 decoration-ink-border"
          >
            NDLS → JP
          </button>
          <span className="text-ink-border">·</span>
          <button
            type="button"
            onClick={() => handleQuickSelect("HWH", "BBS", 2200)}
            className="hover:text-ink-primary transition-colors underline underline-offset-4 decoration-ink-border"
          >
            HWH → BBS
          </button>
          <span className="text-ink-border">·</span>
          <button
            type="button"
            onClick={() => handleQuickSelect("PUNE", "CSMT", 1200)}
            className="hover:text-ink-primary transition-colors underline underline-offset-4 decoration-ink-border"
          >
            PUNE → CSMT
          </button>
          <span className="text-ink-border">·</span>
          <button
            type="button"
            onClick={() => handleQuickSelect("BLR", "MAS", 3500)}
            className="hover:text-ink-primary transition-colors underline underline-offset-4 decoration-ink-border"
          >
            BLR → MAS
          </button>
        </div>
      </div>
    </div>
  );
}
