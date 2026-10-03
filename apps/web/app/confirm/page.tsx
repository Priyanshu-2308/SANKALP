"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { approveRecoveryPlan } from "@/lib/api";
import { ScoredItinerary } from "@/lib/types";

function ConfirmContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tokenParam = searchParams.get("token");
  const itineraryIdParam = searchParams.get("itinerary_id");

  const [itinerary, setItinerary] = useState<ScoredItinerary | null>(null);
  const [token, setToken] = useState<string>("");
  const [originId, setOriginId] = useState<string>("");
  const [destinationId, setDestinationId] = useState<string>("");
  const [timeLeftSeconds, setTimeLeftSeconds] = useState(900); // 15 mins
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const storedItin = sessionStorage.getItem("sankalp_pending_itinerary");
    const storedToken = sessionStorage.getItem("sankalp_approval_token") || tokenParam || "";
    const storedOrigin = sessionStorage.getItem("sankalp_origin_id") || "";
    const storedDest = sessionStorage.getItem("sankalp_destination_id") || "";

    if (storedItin) {
      try {
        setItinerary(JSON.parse(storedItin));
      } catch (e) {
        console.error("Error parsing stored itinerary:", e);
      }
    }
    setToken(storedToken);
    setOriginId(storedOrigin);
    setDestinationId(storedDest);
  }, [tokenParam, itineraryIdParam]);

  // 15-minute countdown timer
  useEffect(() => {
    if (timeLeftSeconds <= 0) return;
    const interval = setInterval(() => {
      setTimeLeftSeconds((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeftSeconds]);

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const handleApprove = async () => {
    if (!itinerary || !token) {
      setErrorMessage("Missing approval token or itinerary state.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await approveRecoveryPlan({
        itinerary_id: itinerary.itinerary_id,
        approval_token: token,
        origin_id: originId || itinerary.legs[0].origin_id,
        destination_id: destinationId || itinerary.legs[itinerary.legs.length - 1].destination_id,
        total_fare_paise: itinerary.total_fare_paise,
        p_ontime: itinerary.metrics.p_ontime,
        itinerary: itinerary,
      });

      // Clear session token to avoid accidental reuse
      sessionStorage.removeItem("sankalp_approval_token");

      // Redirect to live trip monitoring page (query param for static host compatibility)
      router.push(`/trip/?id=${encodeURIComponent(res.trip_id)}`);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMessage(err.message || "Failed to approve recovery itinerary.");
    }
  };

  if (!itinerary) {
    return (
      <div className="w-full max-w-[580px] mx-auto px-4 py-16 text-center">
        <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-8 shadow-sm">
          <h2 className="text-base font-semibold text-ink-primary">No Active Itinerary to Approve</h2>
          <p className="text-xs text-ink-secondary mt-2">
            Please run a search and select an alternative itinerary first.
          </p>
          <div className="mt-6">
            <Link
              href="/"
              className="inline-flex px-4 py-2 rounded-lg bg-primary-container text-white text-xs font-medium"
            >
              Start Search
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[600px] mx-auto px-4 py-10 md:py-14 select-none">
      {/* Step Tracker */}
      <div className="flex items-center justify-between pb-3 mb-6 border-b border-ink-border text-ink-muted text-xs">
        <span className="uppercase tracking-wider font-semibold text-ink-primary">Step 03 / 03</span>
        <span className="uppercase tracking-wider font-medium">Authorization & Locking</span>
      </div>

      {/* Header */}
      <div className="text-left mb-6">
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-ink-primary">
          Confirm Your Recovery Journey
        </h1>
        <p className="text-xs text-ink-secondary mt-1">
          Review the resolved route parameters before atomically redeeming your single-use approval token.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 text-red-900 border border-red-200 text-xs">
          <div className="font-semibold flex items-center gap-1.5">
            <span>⛔ Token Authorization Failed</span>
          </div>
          <p className="mt-1 leading-relaxed">{errorMessage}</p>
        </div>
      )}

      {/* Summary Box */}
      <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-6 shadow-sm mb-6 space-y-4">
        {/* Token Countdown */}
        <div className="flex items-center justify-between pb-3 border-b border-ink-border text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-medium text-ink-secondary">Single-Use Approval Token</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-ink-muted">Expires in:</span>
            <span
              className={`font-mono font-bold text-xs ${
                timeLeftSeconds < 120 ? "text-red-600" : "text-ink-primary"
              }`}
            >
              {formatTimer(timeLeftSeconds)}
            </span>
          </div>
        </div>

        {/* Token String Display */}
        <div className="px-3 py-2 rounded-lg bg-surface-container font-mono text-[11px] text-ink-secondary truncate flex items-center justify-between">
          <span className="truncate">{token || "Generating cryptographic token..."}</span>
          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-surface-container-highest uppercase font-bold text-ink-muted shrink-0">
            15m TTL
          </span>
        </div>

        {/* Route Details */}
        <div className="py-2 border-b border-ink-border space-y-3">
          <div className="flex justify-between items-baseline text-xs">
            <span className="text-ink-secondary">Category:</span>
            <span className="font-semibold text-ink-primary uppercase tracking-wider">{itinerary.tag}</span>
          </div>
          <div className="flex justify-between items-baseline text-xs">
            <span className="text-ink-secondary">Arrival Certainty:</span>
            <span className="font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              {Math.round(itinerary.metrics.p_ontime * 100)}% on-time (95% CI:{" "}
              {(itinerary.metrics.p_ontime_ci_95[0] * 100).toFixed(0)}% –{" "}
              {(itinerary.metrics.p_ontime_ci_95[1] * 100).toFixed(0)}%)
            </span>
          </div>
          <div className="flex justify-between items-baseline text-xs">
            <span className="text-ink-secondary">Duration:</span>
            <span className="font-medium text-ink-primary">
              {Math.floor(itinerary.total_duration_minutes / 60)}h {itinerary.total_duration_minutes % 60}m
            </span>
          </div>
          <div className="flex justify-between items-baseline text-xs">
            <span className="text-ink-secondary">Segments:</span>
            <span className="font-medium text-ink-primary">
              {itinerary.legs.length} leg(s), {itinerary.transfers.length} transfer(s)
            </span>
          </div>
        </div>

        {/* Fare and Action */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <span className="text-[11px] text-ink-muted uppercase tracking-wider">Estimated Fare</span>
            <div className="text-2xl font-bold text-ink-primary">₹{itinerary.total_fare_inr.toLocaleString("en-IN")}</div>
          </div>
        </div>
      </div>

      {/* Disclaimers & Approval Button */}
      <div className="space-y-4">
        <p className="text-[11px] text-ink-muted leading-relaxed">
          <strong>Single-Use Guarantee:</strong> Clicking below executes an atomic SQLite transaction. Once redeemed,
          this token cannot be reused (subsequent attempts return HTTP 410 Gone). An immutable audit log entry is
          recorded in the local database.
        </p>

        <button
          type="button"
          onClick={handleApprove}
          disabled={isSubmitting || timeLeftSeconds <= 0}
          className="w-full py-3 px-6 rounded-lg bg-primary-container hover:bg-primary text-white text-xs font-semibold uppercase tracking-wider transition-colors flex items-center justify-center gap-2 select-none"
        >
          {isSubmitting ? (
            <span>Atomically Redeeming Token...</span>
          ) : timeLeftSeconds <= 0 ? (
            <span>Token Expired — Please Re-Search</span>
          ) : (
            <span>Authorize & Lock Journey</span>
          )}
        </button>

        <div className="text-center">
          <Link
            href="/results"
            className="text-xs text-ink-muted hover:text-ink-primary underline underline-offset-4 decoration-ink-border transition-colors"
          >
            ← Return to Alternatives
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ConfirmPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-xs text-ink-muted">Loading journey confirmation...</div>}>
      <ConfirmContent />
    </Suspense>
  );
}
