"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import TriadCard from "@/components/TriadCard";
import { executeRecoverySearch, requestApprovalToken } from "@/lib/api";
import { RecoverySearchResponse, ScoredItinerary } from "@/lib/types";

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const originId = searchParams.get("origin_id");
  const destinationId = searchParams.get("destination_id");
  const deadline = searchParams.get("deadline");
  const budgetPaise = searchParams.get("budget_paise");

  const [searchResponse, setSearchResponse] = useState<RecoverySearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCardKey, setSelectedCardKey] = useState<string | null>(null);
  const [showPruned, setShowPruned] = useState(false);

  useEffect(() => {
    if (!originId || !destinationId || !deadline) {
      setError("Incomplete search parameters. Please start a new search.");
      setIsLoading(false);
      return;
    }

    async function loadResults() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await executeRecoverySearch({
          origin_id: originId!,
          destination_id: destinationId!,
          deadline: deadline!,
          budget_paise: budgetPaise ? Number(budgetPaise) : undefined,
        });
        setSearchResponse(res);
      } catch (err: any) {
        setError(err.message || "Failed to compute recovery routes.");
      } finally {
        setIsLoading(false);
      }
    }

    loadResults();
  }, [originId, destinationId, deadline, budgetPaise]);

  const handleSelectItinerary = async (itinerary: ScoredItinerary) => {
    const cardKey = `${itinerary.tag || "rec"}-${itinerary.itinerary_id}`;
    setSelectedCardKey(cardKey);
    try {
      const tokenResp = await requestApprovalToken(itinerary.itinerary_id);
      // Store itinerary details in sessionStorage for the confirmation step
      sessionStorage.setItem("sankalp_pending_itinerary", JSON.stringify(itinerary));
      sessionStorage.setItem("sankalp_approval_token", tokenResp.approval_token);
      sessionStorage.setItem("sankalp_origin_id", originId || "");
      sessionStorage.setItem("sankalp_destination_id", destinationId || "");

      router.push(`/confirm?itinerary_id=${itinerary.itinerary_id}&token=${tokenResp.approval_token}`);
    } catch (err: any) {
      alert(`Could not secure single-use token: ${err.message}`);
      setSelectedCardKey(null);
    }
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-[1040px] mx-auto px-4 md:px-8 py-16 flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-2 border-primary-container border-t-transparent rounded-full animate-spin mb-4" />
        <h2 className="text-base font-semibold text-ink-primary">Simulating 10,000 Journey Scenarios...</h2>
        <p className="text-xs text-ink-muted mt-1">
          Evaluating direct and transfer connections across Indian rail, air, and bus corridors.
        </p>
      </div>
    );
  }

  if (error || !searchResponse) {
    return (
      <div className="w-full max-w-[640px] mx-auto px-4 py-16 text-center">
        <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-8 shadow-sm">
          <span className="text-3xl mb-3 block">⚠️</span>
          <h2 className="text-lg font-semibold text-ink-primary">No Viable Recovery Routes Found</h2>
          <p className="text-xs text-ink-secondary mt-2 leading-relaxed">
            {error || "The requested corridor cannot be completed within your deadline or budget constraint."}
          </p>
          <div className="mt-6">
            <Link
              href="/"
              className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg bg-primary-container hover:bg-primary text-white text-xs font-medium transition-colors"
            >
              Modify Search Parameters
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const recs = searchResponse.recommendations;
  const triadList = [recs.safest, recs.balanced, recs.cheapest].filter(Boolean) as ScoredItinerary[];

  return (
    <div className="w-full max-w-[1040px] mx-auto px-4 md:px-8 py-10 md:py-12">
      {/* Search Header Summary */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-6 border-b border-ink-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-semibold text-ink-primary tracking-tight">
              Alternative Routes to {searchResponse.destination.name}
            </h1>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
              {triadList.length} options found
            </span>
          </div>
          <p className="text-xs text-ink-secondary mt-1">
            From {searchResponse.origin.name} ({searchResponse.origin.code}) · Evaluated in{" "}
            <span className="font-semibold text-ink-primary">{searchResponse.execution_time_ms.toFixed(1)}ms</span>{" "}
            via 10k Monte Carlo trials
          </p>
        </div>

        <Link
          href="/"
          className="text-xs font-medium text-ink-secondary hover:text-ink-primary underline underline-offset-4 decoration-ink-border transition-colors self-start sm:self-auto"
        >
          Edit Search
        </Link>
      </div>

      {/* Triad Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-8">
        {triadList.map((itinerary, idx) => {
          const cardKey = `${itinerary.tag || idx}-${itinerary.itinerary_id}`;
          return (
            <TriadCard
              key={cardKey}
              itinerary={itinerary}
              onSelect={handleSelectItinerary}
              isLoading={selectedCardKey === cardKey}
            />
          );
        })}
      </div>

      {/* Pruned Candidates Explanation Accordion */}
      {searchResponse.pruned_candidates.length > 0 && (
        <div className="mt-12 pt-6 border-t border-ink-border">
          <button
            type="button"
            onClick={() => setShowPruned(!showPruned)}
            className="flex items-center justify-between w-full text-left py-2 text-xs font-medium text-ink-secondary hover:text-ink-primary transition-colors"
          >
            <span>
              Decision Engine Audit: Why were other routes excluded? ({searchResponse.pruned_candidates.length}{" "}
              evaluated)
            </span>
            <span className="text-xs">{showPruned ? "▲ Hide" : "▼ Show"}</span>
          </button>

          {showPruned && (
            <div className="mt-3 space-y-2 bg-surface-container-low p-4 rounded-xl border border-ink-border">
              {searchResponse.pruned_candidates.map((pruned, idx) => (
                <div key={idx} className="text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1 py-1.5 border-b border-ink-border/50 last:border-none">
                  <span className="font-medium text-ink-primary">{pruned.itinerary_summary}</span>
                  <span className="text-[11px] text-ink-muted italic">Reason: {pruned.reason_text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="py-16 text-center text-xs text-ink-muted">
          Loading itinerary search results...
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
