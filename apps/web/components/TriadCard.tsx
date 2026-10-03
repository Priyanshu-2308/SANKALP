"use client";

import { ScoredItinerary } from "@/lib/types";

interface TriadCardProps {
  itinerary: ScoredItinerary;
  onSelect: (itinerary: ScoredItinerary) => void;
  isLoading?: boolean;
}

export default function TriadCard({ itinerary, onSelect, isLoading = false }: TriadCardProps) {
  const { tag, plain_reason, metrics, legs, transfers } = itinerary;

  const getTagBadge = () => {
    switch (tag) {
      case "SAFEST":
        return {
          title: "Safest Option",
          subtitle: "Maximum arrival certainty",
          badgeColor: "bg-emerald-50 text-emerald-800 border-emerald-200",
          cardBorder: "border-emerald-600 ring-1 ring-emerald-600/20",
          btnColor: "bg-primary-container hover:bg-primary text-white",
        };
      case "BALANCED":
        return {
          title: "Balanced Option",
          subtitle: "Optimal time vs cost trade-off",
          badgeColor: "bg-blue-50 text-blue-800 border-blue-200",
          cardBorder: "border-ink-border hover:border-blue-400",
          btnColor: "bg-surface-container-lowest hover:bg-surface-container border border-ink-border text-ink-primary",
        };
      case "CHEAPEST":
        return {
          title: "Economical Option",
          subtitle: "Lowest monetary expenditure",
          badgeColor: "bg-amber-50 text-amber-800 border-amber-200",
          cardBorder: "border-ink-border hover:border-amber-400",
          btnColor: "bg-surface-container-lowest hover:bg-surface-container border border-ink-border text-ink-primary",
        };
    }
  };

  const badge = getTagBadge();
  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
    } catch {
      return iso;
    }
  };

  const formatDuration = (mins: number) => {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case "FLIGHT":
        return "✈";
      case "BUS":
        return "🚌";
      case "CAB":
        return "🚕";
      default:
        return "🚆";
    }
  };

  return (
    <div
      className={`bg-surface-container-lowest rounded-xl p-5 md:p-6 flex flex-col justify-between transition-all duration-200 border ${badge.cardBorder} shadow-sm`}
    >
      <div>
        {/* Header Tag */}
        <div className="flex items-center justify-between gap-2 pb-3 border-b border-ink-border">
          <div className="flex flex-col">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
              {badge.title}
            </span>
            <span className="text-[11px] text-ink-muted">{badge.subtitle}</span>
          </div>
          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${badge.badgeColor}`}>
            {Math.round(metrics.p_ontime * 100)}% on-time
          </span>
        </div>

        {/* Price & Primary Summary */}
        <div className="pt-4 pb-2">
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold text-ink-primary tracking-tight">
              ₹{itinerary.total_fare_inr.toLocaleString("en-IN")}
            </span>
            <span className="text-sm font-medium text-ink-secondary">
              {formatDuration(itinerary.total_duration_minutes)}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1 text-xs text-ink-muted">
            <span>
              {formatTime(itinerary.departure_time)} → {formatTime(itinerary.arrival_time)}
            </span>
            <span>·</span>
            <span>{legs.length === 1 ? "Direct" : `${transfers.length} transfer${transfers.length > 1 ? "s" : ""}`}</span>
          </div>
        </div>

        {/* 95% Wilson Score Confidence Interval Badge */}
        <div className="my-3 px-3 py-2 rounded-lg bg-surface-container-low border border-ink-border/60 text-xs">
          <div className="flex items-center justify-between text-[11px] font-medium text-ink-secondary">
            <span>95% Confidence Band</span>
            <span className="font-semibold text-ink-primary">
              {(metrics.p_ontime_ci_95[0] * 100).toFixed(1)}% – {(metrics.p_ontime_ci_95[1] * 100).toFixed(1)}%
            </span>
          </div>
          <p className="text-[10px] text-ink-muted mt-0.5">
            Derived from 10,000 log-normal Monte Carlo simulation trials.
          </p>
        </div>

        {/* Plain Language Rationale */}
        <div className="my-3 p-3 rounded-lg bg-surface-container/50 border border-ink-border text-xs text-ink-secondary leading-relaxed">
          <span className="font-medium text-ink-primary">Rationale: </span>
          {plain_reason}
        </div>

        {/* Journey Legs Timeline */}
        <div className="mt-4 pt-3 border-t border-ink-border space-y-2.5">
          <div className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
            Route Schedule
          </div>
          {legs.map((leg, i) => (
            <div key={`${leg.leg_id || i}_${i}`} className="text-xs">
              <div className="flex items-center justify-between font-medium text-ink-primary">
                <div className="flex items-center gap-1.5">
                  <span>{getModeIcon(leg.mode)}</span>
                  <span>{leg.operator_name}</span>
                  <span className="text-[11px] text-ink-muted">({leg.identifier})</span>
                </div>
                <span>{formatDuration(leg.duration_minutes)}</span>
              </div>
              <div className="text-[11px] text-ink-secondary mt-0.5 flex justify-between">
                <span>
                  {formatTime(leg.departure_time)} – {formatTime(leg.arrival_time)}
                </span>
                <span>₹{leg.fare_inr}</span>
              </div>

              {/* Transfer buffer note */}
              {i < transfers.length && (
                <div className="my-2 py-1 px-2 rounded bg-surface-container text-[11px] text-ink-secondary flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <span>⇄</span>
                    <span>Transfer at intermediate hub</span>
                  </span>
                  <span className="font-medium text-ink-primary">
                    {transfers[i].wait_minutes}m buffer (min {transfers[i].min_connection_minutes}m)
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Action Button */}
      <div className="mt-6 pt-2">
        <button
          type="button"
          onClick={() => onSelect(itinerary)}
          disabled={isLoading}
          className={`w-full py-2.5 px-4 rounded-lg font-medium text-xs transition-colors flex items-center justify-center gap-2 select-none ${badge.btnColor}`}
        >
          {isLoading ? (
            <span>Securing approval token...</span>
          ) : (
            <span>Select & Lock Route</span>
          )}
        </button>
      </div>
    </div>
  );
}
