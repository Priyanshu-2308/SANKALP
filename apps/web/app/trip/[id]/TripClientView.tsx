"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DelaySimulator from "../../../components/DelaySimulator";
import { getTripDetails } from "../../../lib/api";
import { TripDetail } from "../../../lib/types";

export default function TripClientView({ id }: { id: string }) {
  const [trip, setTrip] = useState<TripDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTrip() {
      setIsLoading(true);
      try {
        const data = await getTripDetails(id);
        setTrip(data);
      } catch (err: any) {
        setError(err.message || "Failed to load trip details.");
      } finally {
        setIsLoading(false);
      }
    }

    loadTrip();
  }, [id]);

  if (isLoading) {
    return (
      <div className="w-full max-w-[800px] mx-auto px-4 py-16 flex flex-col items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary-container border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-ink-muted">Loading journey audit log...</p>
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div className="w-full max-w-[600px] mx-auto px-4 py-16 text-center">
        <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-8 shadow-sm">
          <span className="text-3xl mb-3 block">🔍</span>
          <h2 className="text-base font-semibold text-ink-primary">Journey Not Found</h2>
          <p className="text-xs text-ink-secondary mt-1">{error || `No audit record found for Trip ID: ${id}`}</p>
          <div className="mt-6">
            <Link
              href="/"
              className="inline-flex px-4 py-2 rounded-lg bg-primary-container text-white text-xs font-medium"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const itin = trip.itinerary;
  const legs = itin.legs || [];

  return (
    <div className="w-full max-w-[840px] mx-auto px-4 md:px-8 py-10 md:py-12 space-y-8">
      {/* Header and Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-ink-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-semibold text-ink-primary tracking-tight">Active Journey Monitor</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
              {trip.action}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-ink-muted mt-1 font-mono">
            <span>Trip ID: {trip.trip_id}</span>
            <span>·</span>
            <span>Approved: {new Date(trip.created_at).toLocaleTimeString("en-IN")}</span>
          </div>
        </div>

        <Link
          href="/"
          className="text-xs text-ink-secondary hover:text-ink-primary underline underline-offset-4 decoration-ink-border"
        >
          New Search
        </Link>
      </div>

      {/* Itinerary Schedule Card */}
      <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-ink-border text-xs">
          <span className="font-semibold text-ink-primary uppercase tracking-wide">Confirmed Route Plan</span>
          <span className="font-semibold text-ink-primary">Total: ₹{trip.total_fare_inr.toLocaleString("en-IN")}</span>
        </div>

        {/* Legs timeline */}
        <div className="space-y-4 pt-1">
          {legs.map((leg: any, idx: number) => (
            <div key={leg.leg_id || idx} className="flex gap-4 items-start text-xs">
              <div className="w-6 h-6 rounded-full bg-surface-container border border-ink-border flex items-center justify-center font-mono text-[11px] text-ink-secondary shrink-0 mt-0.5">
                {idx + 1}
              </div>
              <div className="flex-1 bg-surface-container-low/50 p-3 rounded-lg border border-ink-border/50">
                <div className="flex items-center justify-between font-medium text-ink-primary">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{leg.operator_name}</span>
                    <span className="text-[11px] text-ink-muted">({leg.identifier})</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-container text-ink-secondary uppercase">
                      {leg.mode}
                    </span>
                  </div>
                  <span>{leg.duration_minutes} min</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-ink-secondary">
                  <div>
                    {new Date(leg.departure_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                    {" → "}
                    {new Date(leg.arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                  </div>
                  <div className="font-medium text-ink-primary">₹{leg.fare_inr || leg.fare_paise / 100}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Embedded Live Delay Simulator */}
      <DelaySimulator
        tripId={trip.trip_id}
        legs={legs}
        originalPOntime={trip.p_ontime}
      />
    </div>
  );
}
